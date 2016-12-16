# Author-Patrick Rainsberry
# Description-Directly publish to OctoPrint

# Referenced heavily from: https://github.com/boboman/Octonomous/blob/master/Octonomous.py


from .octoFusionCommand import octoFusionCommand


commands = []
command_defs = []

# Define parameters for command
cmd = {
        'commandName': 'OctoFusion',
        'commandDescription': 'Export model to OctoPrint',
        'commandResources': './Resources/OctoFusion',
        'cmdId': 'OctoFusion_CmdId',
        'workspace': 'FusionSolidEnvironment',
        'toolbarPanelID': 'SolidMakePanel',
        'class' : octoFusionCommand
}
command_defs.append(cmd)

# Set to True to display various useful messages when debugging your app
debug = False

for cmd_def in command_defs:
    # Creates the commands for use in the Fusion 360 UI
    command = cmd_def['class'](cmd_def, debug)
    commands.append(command)

def run(context):
    for command in commands:
        command.onRun()


def stop(context):
    for command in commands:
        command.onStop()


