<<<<<<< HEAD
#Author-Patrick Rainsberry
#Description-Directly publish to OctoPrint
=======
# Author-Patrick Rainsberry
# Description-Upload FUsion 360 model directly to Octoprint.
# Referenced heavily from: https://github.com/boboman/Octonomous/blob/master/Octonomous.py
>>>>>>> origin/master

import adsk.core, traceback
import adsk.fusion
import tempfile
import uuid
import json
import webbrowser
import importlib
from .packages import requests
from .packages.requests_toolbelt import MultipartEncoder

from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import SubElement

from os.path import expanduser
import os

handlers = []

def getFileName():
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        
        home = expanduser("~")
        home += '/OctoFusion/'
        
        if not os.path.exists(home):
            os.makedirs(home)
        
        xmlFileName = home  + 'settings.xml'
        
        return xmlFileName
    
    except:
        if ui:
            ui.messageBox('Panel command created failed:\n{}'
            .format(traceback.format_exc()))
def writeSettings(xmlFileName, key, profile, printerProfile, host):
    
    if not os.path.isfile(xmlFileName):
        new_file = open( xmlFileName, 'w' )                        
        new_file.write( '<?xml version="1.0"?>' )
        new_file.write( "<OctoFusion /> ")
        new_file.close()
        tree = ElementTree.parse(xmlFileName) 
        root = tree.getroot()
    else:
        # TODO delete node
        tree = ElementTree.parse(xmlFileName) 
        root = tree.getroot()
        root.remove(root.find('settings'))

    settings = SubElement(root, 'settings')
    SubElement(settings, 'printerProfile', value = printerProfile)
    SubElement(settings, 'profile', value = profile)
    SubElement(settings, 'host', value = host)
    SubElement(settings, 'key', value = key)
    
    tree.write(xmlFileName)
    
def readSettings(xmlFileName):
    
    tree = ElementTree.parse(xmlFileName) 
    root = tree.getroot()

    printerProfile = root.find('settings/printerProfile').attrib[ 'value' ]
    profile = root.find('settings/profile').attrib[ 'value' ]
    host = root.find('settings/host').attrib[ 'value' ]
    key = root.find('settings/key').attrib[ 'value' ]
    
    return(printerProfile, profile, host, key)
    
def upload_file(filepath, filename, host, key):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        m = MultipartEncoder(
            fields={
                'file': (filename, open(filepath, 'rb'), 'application/octet-stream'),
                'select': 'false',
                'print': 'false'
            }
        )
    
        url = 'http://' + host + '/api/files/local'
    
        # m.content_type is required here as it will append the boundary token to the content type.
        headers = {'Content-Type': m.content_type, 'X-Api-Key': key}
        r = requests.post(url, data=m, headers=headers)

    except requests.exceptions.ConnectTimeout as e:
        if ui:
            ui.messageBox('Connection timed out.')
        return
    except requests.exceptions.ConnectionError as e:
        if ui:
            ui.messageBox('Error connecting to Octoprint site.')
        return

    if r.status_code != 201:
        if ui:
            ui.messageBox('Error posting file to Octoprint site. (Error ' + str(r.status_code) + ')')
        return


def home_xyz(host, key):

    headers = {'content-type': 'application/json', 'X-Api-Key': key}
    payload = {'command': 'home', 'axes': ["x", "y", "z"]}
    url = 'http://' + host + '/api/printer/printhead'

    r = requests.post(url, data=json.dumps(payload), headers=headers)

    print(str(r.status_code))

    if r.status_code == 204:
        print("Printer is homing the X,Y,Z axes ...")
    elif r.status_code == 400:
        print("Critical Error: Bad Request")
    elif r.status_code == 409:
        print("The printer is either already printing or not operational.")

def octoSlice(filename, printerProfile, profile, startPrint, host, key):
    headers = {'content-type': 'application/json', 'X-Api-Key': key}
    payload = {
        "command": "slice",
        "slicer": "cura",
        "gcode": filename + '.gcode',
        "printerProfile": printerProfile,
        "profile": profile,
        #"profile.infill": 75,
        #"profile.fill_density": 15,
        #"position": {"x": 100, "y": 100},
        "print": startPrint
        }
    url = 'http://' + host + '/api/files/local/'+filename+'.stl'

    r = requests.post(url, data=json.dumps(payload), headers=headers)
    print(str(r.status_code))

def exportFile(stlRefinement, selection, filename):

    # Get the ExportManager from the active design.
    app = adsk.core.Application.get()
    design = app.activeProduct
    exportMgr = design.exportManager

    # Create a temporary directory.
    tempDir = tempfile.mkdtemp()

    # Export the file.
    # If you want to randomize the file name
#    resultFilename = tempDir + '//' + str(uuid.uuid1())
    resultFilename = tempDir + '//' + filename
    resultFilename = resultFilename + '.stl'
    stlOptions = exportMgr.createSTLExportOptions(selection, resultFilename)
    
    if stlRefinement == 'Low':
        stlOptions.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementLow
    elif stlRefinement == 'Medium':
        stlOptions.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementMedium
    elif stlRefinement == 'High':
        stlOptions.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh

    exportMgr.execute(stlOptions)
    
    return resultFilename

# Get the current values of the command inputs.
def getInputs(inputs):
    try:
        stlRefinementInput = inputs.itemById('stlRefinement')
        stlRefinement = stlRefinementInput.selectedItem.name
    
        selection = inputs.itemById('selection').selection(0).entity
        if selection.objectType == adsk.fusion.Occurrence.classType():
            selection = selection.component
        
        startPrint = inputs.itemById('startPrint').value
        key = inputs.itemById('key').text
        profile = inputs.itemById('profile').text
        printerProfile = inputs.itemById('printerProfile').text
        host = inputs.itemById('host').text
        saveSettings = inputs.itemById('saveSettings').value

        return (stlRefinement, selection, startPrint, key, profile, printerProfile, host, saveSettings)
    except:
        app = adsk.core.Application.get()
        ui = app.userInterface
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

# Define the event handler for Octoprint command is executed (the "Create RFQ" button is clicked on the dialog).
class FusionOctoprintExecutedEventHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):

        ui = []
        try:
            app = adsk.core.Application.get()
            ui  = app.userInterface

            # Get the inputs.
            inputs = args.command.commandInputs
            (stlRefinement, selection, startPrint, key, profile, printerProfile, host, saveSettings) = getInputs(inputs)
            filename = selection.name
            resultFilename = exportFile(stlRefinement, selection, filename)
            
            if saveSettings:
                xmlFileName = getFileName()
                writeSettings(xmlFileName, key, profile, printerProfile, host)

            # Connect to the server and Upload
            upload_file(resultFilename, filename+'.stl', host, key)
            
            # Slice and start printing
            if startPrint:
                home_xyz(host, key)
                octoSlice(filename, printerProfile, profile, startPrint, host, key)
            
            # Launch local browser
            url = 'http://' + host
            webbrowser.open_new(url)
            
        except:

            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Define the event handler for when any input changes.
class FusionOctoprintInputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        ui = []
        try:
            app = adsk.core.Application.get()
            ui  = app.userInterface

            input = args.input

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

                
# Define the event handler for when the command is activated.
class FusionOctoprintCommandActivatedHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        ui = []
        try:
            app = adsk.core.Application.get()
            ui  = app.userInterface

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

                
# Define the event handler for when the Octoprint command is run by the user.
class FusionOctoprintCreatedEventHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        ui = []
        try:
            app = adsk.core.Application.get()
            ui  = app.userInterface

            # Connect to the command executed event.
            cmd = args.command
            cmd.isExecutedWhenPreEmpted = False
            onExecute = FusionOctoprintExecutedEventHandler()
            cmd.execute.add(onExecute)
            handlers.append(onExecute)

            onInputChanged = FusionOctoprintInputChangedHandler()
            cmd.inputChanged.add(onInputChanged)
            handlers.append(onInputChanged)
            
            # Connect to the command activated event.
            onActivate = FusionOctoprintCommandActivatedHandler()
            cmd.activate.add(onActivate)
            handlers.append(onActivate)

            # Define the inputs.
            inputs = cmd.commandInputs
            
            inputs.addImageCommandInput('image1', '', './/Resources//octoprint-logo.png')
            #inputs.addTextBoxCommandInput('labelText1', '', '<a href="http://www.Octoprint.com">www.Octoprint.com</a></span>', 1, True)
            inputs.addTextBoxCommandInput('labelText2', '', '<a href="http://octoprint.org">www.Octoprint.org</a></span> The snappy web interface for your 3D printer', 4, True)
            
            
            inputs.addTextBoxCommandInput('labelText3', '', 'Choose the file type and selection to send to Octoprint for quotes.', 2, True)


            stldropDown = inputs.addDropDownCommandInput('stlRefinement', 'STL refinement', adsk.core.DropDownStyles.LabeledIconDropDownStyle)
            stldropDown.listItems.add('Low', False)
            stldropDown.listItems.add('Medium', True)
            stldropDown.listItems.add('High', False)

            selection = inputs.addSelectionInput('selection', 'Selection', 'Select the body or component to quote' )
            selection.addSelectionFilter('Occurrences')
            selection.addSelectionFilter('RootComponents')
#            selection.addSelectionFilter('SolidBodies')
            
            host_input = inputs.addTextBoxCommandInput('host', 'Local Host Address: ', 'Local Address to OctoPrint Server', 1, False)
            key_input =  inputs.addTextBoxCommandInput('key', 'API Key: ', 'Get your API Key from settings dialog', 1, False)
            
            # TODO Add look up of existing profiles            
            printerProfile_input = inputs.addTextBoxCommandInput('printerProfile', 'Printer Profile: ', 'Name of Printer Profile', 1, False)
            profile_input = inputs.addTextBoxCommandInput('profile', 'Slicing Profile: ', 'Name of Slicer Profile', 1, False)
            
            inputs.addBoolValueInput("startPrint", 'Start Printing Immediately?', True)
            inputs.addBoolValueInput("saveSettings", 'Save settings?', True)
            
            cmd.commandCategoryName = 'Octoprint'
            cmd.setDialogInitialSize(500, 300)
            cmd.setDialogMinimumSize(500, 300)

            cmd.okButtonText = 'Ok'
            
            xmlFileName = getFileName()
            if os.path.isfile(xmlFileName):
                (printerProfile, profile, host, key) = readSettings(xmlFileName)
                host_input.text = host
                key_input.text = key
                printerProfile_input.text = printerProfile
                profile_input.text = profile

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def run(context):
    ui = None

    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface

        if ui.commandDefinitions.itemById('OctoprintButtonID'):
            ui.commandDefinitions.itemById('OctoprintButtonID').deleteMe()

        # Get the CommandDefinitions collection.
        cmdDefs = ui.commandDefinitions

        # Create a button command definition for the comamnd button.  This
        # is also used to display the disclaimer dialog.
        tooltip = '<div style=\'font-family:"Calibri";color:#B33D19; padding-top:-20px;\'><span style=\'font-size:20px;\'><b>Octoprint.org</b></span></div>The snappy web interface for your 3D printer'
        FusionOctoprintButtonDef = cmdDefs.addButtonDefinition('OctoprintButtonID', 'Print with OctoPrint', tooltip, './/Resources//OctoFusion')
        onOctoprintCreated = FusionOctoprintCreatedEventHandler()
        FusionOctoprintButtonDef.commandCreated.add(onOctoprintCreated)
        handlers.append(onOctoprintCreated)

        # Find the "ADD-INS" panel for the solid and the surface workspaces.
        solidPanel = ui.allToolbarPanels.itemById('SolidMakePanel')
        surfacePanel = ui.allToolbarPanels.itemById('SurfaceMakePanel')
        
        # Add a button for the "Request Quotes" command into both panels.
        buttonControl = solidPanel.controls.addCommand(FusionOctoprintButtonDef, '', False)
        buttonControl = surfacePanel.controls.addCommand(FusionOctoprintButtonDef, '', False)
    except:
        pass
        #if ui:
        #    ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def stop(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface

        if ui.commandDefinitions.itemById('OctoprintButtonID'):
            ui.commandDefinitions.itemById('OctoprintButtonID').deleteMe()

        # Find the controls in the solid and surface panels and delete them.
        solidPanel = ui.allToolbarPanels.itemById('SolidMakePanel')
        cntrl = solidPanel.controls.itemById('OctoprintButtonID')
        if cntrl:
            cntrl.deleteMe()

        surfacePanel = ui.allToolbarPanels.itemById('SurfaceMakePanel')
        cntrl = surfacePanel.controls.itemById('OctoprintButtonID')
        if cntrl:
            cntrl.deleteMe()

    except:
        pass
        #if ui:
        #    ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
