import adsk.core, traceback
import adsk.fusion

import tempfile
import json
import webbrowser
from .packages import requests
from .packages.requests_toolbelt import MultipartEncoder

from xml.etree import ElementTree
from xml.etree.ElementTree import SubElement

from os.path import expanduser
import os

from .Fusion360CommandBase import Fusion360CommandBase


# Creates directory and returns file name for settings file
def get_file_name():
    # Get Home directory
    home = expanduser("~")
    home += '/OctoFusion/'

    # Create if doesn't exist
    if not os.path.exists(home):
        os.makedirs(home)

    # Create file name in this path
    xmlFileName = home + 'settings.xml'
    return xmlFileName


# Writes user settings to a file in local home directory
def write_settings(xml_file_name, key, slicer_profile, printer_profile, host):
    # If file doesn't exist create it
    if not os.path.isfile(xml_file_name):
        new_file = open(xml_file_name, 'w')
        new_file.write('<?xml version="1.0"?>')
        new_file.write("<OctoFusion /> ")
        new_file.close()
        tree = ElementTree.parse(xml_file_name)
        root = tree.getroot()
    # Otherwise delete existing settings
    else:
        tree = ElementTree.parse(xml_file_name)
        root = tree.getroot()
        root.remove(root.find('settings'))

    # Write settings
    settings = SubElement(root, 'settings')
    SubElement(settings, 'printerProfile', value=printer_profile)
    SubElement(settings, 'profile', value=slicer_profile)
    SubElement(settings, 'host', value=host)
    SubElement(settings, 'key', value=key)
    tree.write(xml_file_name)


# Read user settings in from XML file 
def read_settings(xmlFileName):
    # Get the root of the XML tree
    tree = ElementTree.parse(xmlFileName)
    root = tree.getroot()

    # Get the settings values
    printer_profile = root.find('settings/printerProfile').attrib['value']
    profile = root.find('settings/profile').attrib['value']
    host = root.find('settings/host').attrib['value']
    key = root.find('settings/key').attrib['value']

    return printer_profile, profile, host, key


# Upload file to OctoPrint server via OctoPrint API
def upload_file(file_path, filename, host, key):
    app = adsk.core.Application.get()
    ui = app.userInterface

    # Using multipart encoder from requests toolkit
    m = MultipartEncoder(
        fields={
            'file': (filename, open(file_path, 'rb'), 'application/octet-stream'),
            'select': 'false',
            'print': 'false'
        }
    )

    # Construct URL for API call
    url = 'http://' + host + '/api/files/local'

    # m.content_type is required here as it will append the boundary token to the content type.
    headers = {'Content-Type': m.content_type, 'X-Api-Key': key}
    r = requests.post(url, data=m, headers=headers)

    # Check for connection errors
    if r.status_code != 201:
        ui.messageBox('Error posting file to Octoprint site. Check your API key. (Error ' + str(r.status_code) + ')')

    return


# Home XYZ Axis on printer via OctoPrint API
def home_xyz(host, key):
    app = adsk.core.Application.get()
    ui = app.userInterface

    # Construct URL for OctoPrint API call using requests
    headers = {'content-type': 'application/json', 'X-Api-Key': key}
    payload = {'command': 'home', 'axes': ["x", "y", "z"]}
    url = 'http://' + host + '/api/printer/printhead'
    r = requests.post(url, data=json.dumps(payload), headers=headers)

    # Error check response
    if r.status_code == 204:
        ui.messageBox("Printer is homing the X,Y,Z axes ...")
    elif r.status_code == 400:
        ui.messageBox("Critical Error: Bad Request")
    elif r.status_code == 409:
        ui.messageBox("The printer is either already printing or not operational.")
    else:
        ui.messageBox('Error homing machine. Check your API key. (Error ' + str(r.status_code) + ')')

    return


# Slice the exported file using Cura slicing engine
def octo_slice(filename, printerProfile, slicerProfile, startPrint, host, key):
    app = adsk.core.Application.get()
    ui = app.userInterface

    # Construct URL for OctoPrint API call using requests
    headers = {'content-type': 'application/json', 'X-Api-Key': key}
    payload = {
        "command": "slice",
        "slicer": "cura",
        "gcode": filename + '.gcode',
        "printerProfile": printerProfile,
        "profile": slicerProfile,
        # "profile.infill": 75,
        # "profile.fill_density": 15,
        # "position": {"x": 100, "y": 100},
        "print": startPrint
    }
    url = 'http://' + host + '/api/files/local/' + filename + '.stl'
    r = requests.post(url, data=json.dumps(payload), headers=headers)

    # Error check response
    if r.status_code == 202:
        ui.messageBox("Slicing Successful")
    elif r.status_code == 400:
        ui.messageBox("Critical Error: Bad Request")
    elif r.status_code == 415:
        ui.messageBox("Unsupported Media Type for Slicing")
    elif r.status_code == 404:
        ui.messageBox("File not found on Server.  Something happened during export")
    elif r.status_code == 409:
        ui.messageBox("The printer is either already printing or not operational.")

    return


# Gets printer and slicer profiles from OctoPrint API
# Sets values in drop downs
def octoProfiles(key, host, slicer_input, printer_input):
    app = adsk.core.Application.get()
    ui = app.userInterface

    # Get the printer profiles 
    headers = {'content-type': 'application/json', 'X-Api-Key': key}
    url = 'http://' + host + '/api/printerprofiles'
    try:
        r = requests.get(url, headers=headers)
    except:
        if ui:
            ui.messageBox('Failed to connect to: ' + url)
        return

    # Check Response
    if r.status_code != 200:
        ui.messageBox('Error reading from Octoprint site. (Error ' + str(r.status_code) + ')')
        return
    elif r.encoding is not None:
        ui.messageBox('No data recieved from server, check server name')
        return

    # If response is good encode into json object to parse
    data = r.json()

    # Update List items for printer profiles
    for printer in data["profiles"]:
        printer_input.listItems.add(printer, False)

        # Get Slicer Profiles
    url = 'http://' + host + '/api/slicing/cura/profiles'
    r = requests.get(url, headers=headers)

    # Check Response
    if r.status_code != 200:
        ui.messageBox('Error reading from Octoprint site. (Error ' + str(r.status_code) + ')')
        return
    elif r.encoding is not None:
        ui.messageBox('No data recieved from server, check server name')
        return

    # If response is good encode into json object to parse        
    data = r.json()

    # Update List items for printer profiles
    for slicer in data:
        slicer_input.listItems.add(slicer, False)

    return


# Export an STL file of selection to local temp directory
def export_file(stl_refinement, selection, filename):

    # Get the ExportManager from the active design.
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    export_mgr = design.exportManager

    # Set model units to mm for export to cura engine
    fusion_units_manager = design.fusionUnitsManager
    current_units = fusion_units_manager.distanceDisplayUnits
    fusion_units_manager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits

    # Create a temporary directory.
    temp_dir = tempfile.mkdtemp()

    # If you want to randomize the file name
    # resultFilename = tempDir + '//' + str(uuid.uuid1())

    # Create temp file name 
    result_filename = temp_dir + '//' + filename
    result_filename = result_filename + '.stl'

    # Create export options for STL export    
    stl_options = export_mgr.createSTLExportOptions(selection, result_filename)

    # Set export options based on refinement drop down: 
    if stl_refinement == 'Low':
        stl_options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementLow
    elif stl_refinement == 'Medium':
        stl_options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementMedium
    elif stl_refinement == 'High':
        stl_options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh

    # Execute Export command
    export_mgr.execute(stl_options)

    fusion_units_manager.distanceDisplayUnits = current_units

    return result_filename


# Get the current values of the command inputs.
def get_inputs(inputs):
    try:
        stlRefinementInput = inputs.itemById('stlRefinement')
        stlRefinement = stlRefinementInput.selectedItem.name

        selection = inputs.itemById('selection').selection(0).entity
        if selection.objectType == adsk.fusion.Occurrence.classType():
            selection = selection.component

        startPrint = inputs.itemById('startPrint').value
        key = inputs.itemById('key').text
        slicerProfile = inputs.itemById('slicerProfile').selectedItem.name
        printerProfile = inputs.itemById('printerProfile').selectedItem.name
        host = inputs.itemById('host').text
        saveSettings = inputs.itemById('saveSettings').value

        return stlRefinement, selection, startPrint, key, slicerProfile, printerProfile, host, saveSettings
    except:
        app = adsk.core.Application.get()
        ui = app.userInterface
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


############# Create your Actions Here #################################################
class octoFusionCommand(Fusion360CommandBase):
    # Runs when when any input in the command dialog is changed
    def onInputChanged(self, command, inputs, changedInput):

        # Get current input values
        slicer_input = inputs.itemById('slicerProfile')
        printer_input = inputs.itemById('printerProfile')
        host = inputs.itemById('host').text
        key = inputs.itemById('key').text

        # Refresh the dropdowns for printer and slicer profiles
        if changedInput.id == 'refresh':
            octoProfiles(key, host, slicer_input, printer_input)
            changedInput.selectedItem.isSelected = False

        # Home the printer head with OctoPrint API
        elif changedInput.id == 'home':
            home_xyz(host, key)
            changedInput.selectedItem.isSelected = False

    # Runs when the user presses ok button
    def onExecute(self, command, inputs):

        # Get the inputs.
        (stlRefinement, selection, startPrint, key, slicerProfile, printerProfile, host, saveSettings) = get_inputs(
            inputs)
        filename = selection.name

        # Export the selected file as an STL to temp directory            
        result_filename = export_file(stlRefinement, selection, filename)

        # Optionally save the users settings to a local XML
        if saveSettings:
            xml_file_name = get_file_name()
            write_settings(xml_file_name, key, slicerProfile, printerProfile, host)

        # Connect to the OctoPrint server and upload the new file
        upload_file(result_filename, filename + '.stl', host, key)

        # If user is going to print, first home machine
        if startPrint:
            home_xyz(host, key)

        # Slice and start printing if user has selected to do so
        octo_slice(filename, printerProfile, slicerProfile, startPrint, host, key)

        # Launch local browser and display OctoPrint page
        url = 'http://' + host
        webbrowser.open_new(url)

    # Runs when user selects your command from Fusion UI, Build UI here
    def onCreate(self, command, inputs):

        inputs.addImageCommandInput('image1', '', './/Resources//octoprint-logo.png')
        inputs.addTextBoxCommandInput('labelText2', '',
                                      '<a href="http://octoprint.org">www.Octoprint.org</a></span> The snappy web interface for your 3D printer',
                                      4, True)
        inputs.addTextBoxCommandInput('labelText3', '',
                                      'Choose the file type and selection to send to Octoprint for quotes.', 2, True)

        stldropDown = inputs.addDropDownCommandInput('stlRefinement', 'STL refinement',
                                                     adsk.core.DropDownStyles.LabeledIconDropDownStyle)
        stldropDown.listItems.add('Low', False)
        stldropDown.listItems.add('Medium', True)
        stldropDown.listItems.add('High', False)

        selection = inputs.addSelectionInput('selection', 'Selection', 'Select the component to print')
        selection.addSelectionFilter('Occurrences')
        selection.addSelectionFilter('RootComponents')
        #            selection.addSelectionFilter('SolidBodies')

        host_input = inputs.addTextBoxCommandInput('host', 'Local Host Address: ', 'Local Address to OctoPrint Server',
                                                   1, False)
        key_input = inputs.addTextBoxCommandInput('key', 'API Key: ', 'Get your API Key from settings dialog', 1, False)

        refresh_buttonRowInput = inputs.addButtonRowCommandInput('refresh', 'Refresh Profiles', False)
        refresh_buttonRowInput.listItems.add('Refresh Profiles', False, 'Resources')

        printer_input = inputs.addDropDownCommandInput('printerProfile', 'Printer Profile: ',
                                                       adsk.core.DropDownStyles.LabeledIconDropDownStyle)
        slicer_input = inputs.addDropDownCommandInput('slicerProfile', 'Slicing Profile: ',
                                                      adsk.core.DropDownStyles.LabeledIconDropDownStyle)

        home_buttonRowInput = inputs.addButtonRowCommandInput('home', 'Home Machine Now', False)
        home_buttonRowInput.listItems.add('Home Machine', False, 'Resources')

        inputs.addBoolValueInput("startPrint", 'Start Printing Immediately?', True)
        inputs.addBoolValueInput("saveSettings", 'Save settings?', True)

        command.setDialogInitialSize(500, 300)
        command.setDialogMinimumSize(300, 300)

        command.okButtonText = 'Ok'

        # Get filename for settings file
        xml_file_name = get_file_name()

        # If there is a local settings file apply the values
        if os.path.isfile(xml_file_name):
            (printerProfile, slicerProfile, host, key) = read_settings(xml_file_name)
            host_input.text = host
            key_input.text = key

            # Update drop down values based on currently available profiles
            octoProfiles(key, host, slicer_input, printer_input)

            # Set the profiles to the user's saved settings
            for item in slicer_input.listItems:
                if item.name == slicerProfile:
                    item.isSelected = True
            for item in printer_input.listItems:
                if item.name == printerProfile:
                    item.isSelected = True
