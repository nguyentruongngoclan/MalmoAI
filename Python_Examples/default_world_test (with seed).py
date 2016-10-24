# ------------------------------------------------------------------------------------------------
# Copyright (c) 2016 Microsoft Corporation
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
# associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute,
# sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
# NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# ------------------------------------------------------------------------------------------------

# Sample to demonstrate use of the DefaultWorldGenerator, ContinuousMovementCommands, timestamps and ObservationFromFullStats.
# Runs an agent in a standard Minecraft world, randomly seeded, uses timestamps and observations
# to calculate speed of movement, and chooses tiny "programmes" to execute if the speed drops to below a certain threshold.
# Mission continues until the agent dies.

import MalmoPython
import os
import random
import sys
import time
import datetime
import json
import random

#def updateMapKnowledgeBase (agentPos, observationPercept, mapKnowledegeBase):
#    for i in range(len(observationPercept)):
#        # assume yaw is 0.0, which mean the agent is facing at the +z direction
#    return

def GetMissionXML():
    ''' Build an XML mission string that uses the DefaultWorldGenerator.'''
    
    return '''<?xml version="1.0" encoding="UTF-8" ?>
    <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <About>
            <Summary>Normal life</Summary>
        </About>

        <ServerSection>
            <ServerHandlers>
                <DefaultWorldGenerator seed="-4768167294082842578"/>                
            </ServerHandlers>
        </ServerSection>

        <AgentSection mode="Survival">
            <Name>Rover</Name>
            <AgentStart>
                <Placement x="115" y="66" z="174"/>
                <Inventory>
                    <InventoryBlock slot="0" type="glowstone" quantity="63"/>
                </Inventory>
            </AgentStart>
            <AgentHandlers>                
                <ObservationFromGrid>
                    <Grid name="Cube3x5x3">
                        <min x="-1" y="-1" z="-1"/>
                        <max x="1" y="3" z="1"/>
                    </Grid>
                </ObservationFromGrid>
                <ContinuousMovementCommands/>
                <ObservationFromFullStats/>
            </AgentHandlers>
        </AgentSection>

    </Mission>'''
  
# Variety of strategies for dealing with loss of motion:
commandSequences=[
    #"jump 1; move 1; wait 1; jump 0; move 1; wait 2",   # attempt to jump over obstacle
    #"turn 0.5; wait 1; turn 0; move 1; wait 2",         # turn right a little
    #"turn -0.5; wait 1; turn 0; move 1; wait 2",        # turn left a little
    #"move 0; attack 1; wait 5; pitch 0.5; wait 1; pitch 0; attack 1; wait 5; pitch -0.5; wait 1; pitch 0; attack 0; move 1; wait 2", # attempt to destroy some obstacles
    #"move 0; pitch 1; wait 2; pitch 0; use 1; jump 1; wait 6; use 0; jump 0; pitch -1; wait 1; pitch 0; wait 2; move 1; wait 2" # attempt to build tower under our feet
]

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately

my_mission = MalmoPython.MissionSpec(GetMissionXML(), True)

agent_host = MalmoPython.AgentHost()
try:
    agent_host.parse( sys.argv )
except RuntimeError as e:
    print 'ERROR:',e
    print agent_host.getUsage()
    exit(1)
if agent_host.receivedArgument("help"):
    print agent_host.getUsage()
    exit(0)

if agent_host.receivedArgument("test"):
    my_mission.timeLimitInSeconds(20) # else mission runs forever

# Attempt to start the mission:
max_retries = 3
for retry in range(max_retries):
    try:
        agent_host.startMission( my_mission, MalmoPython.MissionRecordSpec() )
        break
    except RuntimeError as e:
        if retry == max_retries - 1:
            print "Error starting mission",e
            print "Is the game running?"
            exit(1)
        else:
            time.sleep(2)

# Wait for the mission to start:
world_state = agent_host.getWorldState()
while not world_state.has_mission_begun:
    time.sleep(0.1)
    world_state = agent_host.getWorldState()

currentSequence="move 1; wait 4"    # start off by moving
currentSpeed = 0.0
distTravelledAtLastCheck = 0.0
timeStampAtLastCheck = datetime.datetime.now()
cyclesPerCheck = 10 # controls how quickly the agent responds to getting stuck, and the amount of time it waits for on a "wait" command.
currentCycle = 0
waitCycles = 0

# LAN:  Agent's knowlegde gathered from it's observationPercept will be recorded in this mapKnowledgeBase as a dictionary
#       mapKnowlegdeBase is a map: [int, int, int] -> string
#           where the key [int, int, int] is a 1-D array of 3 integer elements x,y,z, where x,y,z are coordinates of the map oberserved respectively
#           and the value string is the name of the block at the (x,y,z) position learned by the agent
mapKnowledgeBase = {};

# Main loop:
while world_state.is_mission_running:
    world_state = agent_host.getWorldState()
    if world_state.number_of_observations_since_last_state > 0:
        obvsText = world_state.observations[-1].text
        currentCycle += 1
        if currentCycle == cyclesPerCheck:  # Time to check our speed and decrement our wait counter (if set):
            currentCycle = 0
            if waitCycles > 0:
                waitCycles -= 1
            # Now use the latest observation to calculate our approximate speed:
            data = json.loads(obvsText) # observation comes in as a JSON string...

            # LAN:  The agent is able to look around it in a 3x5x3 block
            #       If the agent is standing at (x,y,z) position
            #           Then it can see 3x3 square from position (x,y-2,z) to (x,y+3,z) where it's standing
            #       NOTE: I will restrict the case where it can only see the position (x+i, y-2, z+j) if and only if position (x+i, y-1, z+j)
            #             is an air block. (-1 <= i,j <= 1)
            observationPercept = data.get(u'Cube3x5x3',0);

            # LAN: agentPos is an 1D array of 3 elements x,y,z where x,y,z are the integer coordinates of the current position of the agent
            agentPos = [int(data.get(u'XPos')), int(data.get(u'YPos')), int(data.get(u'ZPos'))];
            agentYaw = data.get(u'Yaw')
            
            print agentYaw, agentPos, [(data.get(u'XPos')), (data.get(u'YPos')), (data.get(u'ZPos'))];
            print "standing on", observationPercept[4];
            print "layer 1:", observationPercept[9:18];
            print "layer 2:", observationPercept[18:27];

            # Lan: Update the agent's knowledge of the world
            #updateMapKnowlegdeBase(agentPos, observationPercept, mapKnowledegeBase);
            dist = data.get(u'DistanceTravelled', 0)    #... containing a "DistanceTravelled" field (amongst other things).
            timestamp = world_state.observations[-1].timestamp  # timestamp arrives as a python DateTime object

            delta_dist = dist - distTravelledAtLastCheck
            delta_time = timestamp - timeStampAtLastCheck
            currentSpeed = 1000000.0 * delta_dist / float(delta_time.microseconds)  # "centimetres" per second?
            
            distTravelledAtLastCheck = dist
            timeStampAtLastCheck = timestamp

    if waitCycles == 0:
        # Time to execute the next command, if we have one:
        if currentSequence != "":
            commands = currentSequence.split(";", 1)
            command = commands[0].strip()
            if len(commands) > 1:
                currentSequence = commands[1]
            else:
                currentSequence = ""
            #print command
            verb,sep,param = command.partition(" ")
            if verb == "wait":  # "wait" isn't a Malmo command - it's just used here to pause execution of our "programme".
                waitCycles = int(param.strip())
            else:
                agent_host.sendCommand(command)    # Send the command to Minecraft.
                
    if currentSequence == "" and currentSpeed < 50 and waitCycles == 0: # Are we stuck?
        currentSequence = random.choice(commandSequences)   # Choose a random action (or insert your own logic here for choosing more sensibly...)
        #print "Stuck! Chosen programme: " + currentSequence

# Mission has ended.
