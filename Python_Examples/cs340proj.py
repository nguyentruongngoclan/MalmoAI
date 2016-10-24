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

# Tutorial sample #2: Run simple mission using raw XML

import MalmoPython
import os
import random
import sys
import time
import json

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately

# LAN
# Assume we have a cubic (x1,y1,z1) (x2,y2,z2) , we put some different block type inside the cubic
def RandomizeBlockType(x1, y1, z1, x2, y2, z2, randomItemMapSet, baseBlock):
    genstring = ""
    for item in randomItemMapSet:
        for iterator in range(randomItemMapSet[item]):     
            x_random = random.randint(x1, x2)
            y_random = random.randint(y1, y2)
            z_random = random.randint(z1, z2)            
            print(item, x_random, y_random, z_random) #Debugging output         
            genstring += '<DrawBlock type="' + item + '" x="' + str(x_random) + '" y="' + str(y_random) + '" z="' + str(z_random) + '"/>' + "\n"
                            
    return genstring
        
# LAN
# Generating a cubic block
def DrawCuboid(x1, y1, z1, x2, y2, z2, blocktype):
    return '<DrawCuboid x1="' + str(x1) + '" y1="' + str(y1) + '" z1="' + str(z1) + '" x2="' + str(x2) + '" y2="' + str(y2) + '" z2="' + str(z2) + '" type="' + blocktype + '"/>' + "\n"

# LAN
# Generating the cubic world for the agent
# The cubic world have:
#   irons: # of irons
#   diamonds: # of diamonds
#   x1,y1,z1: Original coordinate of the cube
#   x2,y2,z2: The ending coordinate of the cube, after expanded from x1,y1,z1
def DrawCubicWorld(x1, y1, z1, x2, y2, z2, baseBlock):
    cubicWorld = DrawCuboid(x1, y1, z1, x2, y2, z2, baseBlock)
    randomItemMapSet = {'diamond_ore': 1, 'iron_ore': 10}
    cubicWorld += RandomizeBlockType(x1, y1, z1, x2, y2, z2, randomItemMapSet, baseBlock)
    return cubicWorld

# More interesting generator string: "3;7,44*49,73,35:1,159:4,95:13,35:13,159:11,95:10,159:14,159:6,35:6,95:6;12;"

missionXML='''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
            <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            
              <About>
                <Summary>Hello world!</Summary>
              </About>
              
              <ServerSection>
                <ServerInitialConditions>
                  <Time>
                    <StartTime>12000</StartTime>
                    <AllowPassageOfTime>false</AllowPassageOfTime>
                  </Time>
                </ServerInitialConditions>
                <ServerHandlers>
                  <FlatWorldGenerator generatorString="3;7,220*1,5*3,2;3;,biome_1"/>
                  <DrawingDecorator>
                       ''' + DrawCubicWorld(207, 207, 207, 226, 226, 226, "stone") + '''
                  </DrawingDecorator>
                  <ServerQuitFromTimeUp timeLimitMs="300000"/>
                  <ServerQuitWhenAnyAgentFinishes/>
                </ServerHandlers>
              </ServerSection>
              
              <AgentSection mode="Survival">
                <Name>MalmoTutorialBot</Name>
                <AgentStart>
                    <Placement x="226" y="227" z="226.5" yaw="90"/>
                    <Inventory>
                        <InventoryItem slot="0" type="iron_pickaxe"/>
                    </Inventory>
                </AgentStart>
                <AgentHandlers>
                  <ObservationFromFullStats/>
                  <ObservationFromGrid>
                      <Grid name="cube3x3x3">
                        <min x="-1" y="-1" z="-1"/>
                        <max x="1" y="1" z="1"/>
                      </Grid>
                  </ObservationFromGrid>
                  <ContinuousMovementCommands turnSpeedDegs="180"/>
                </AgentHandlers>
              </AgentSection>
            </Mission>'''

# Create default Malmo objects:

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

my_mission = MalmoPython.MissionSpec(missionXML, True)
my_mission_record = MalmoPython.MissionRecordSpec()

# Attempt to start a mission:
max_retries = 3
for retry in range(max_retries):
    try:
        agent_host.startMission( my_mission, my_mission_record )
        break
    except RuntimeError as e:
        if retry == max_retries - 1:
            print "Error starting mission:",e
            exit(1)
        else:
            time.sleep(2)

# Loop until mission starts:
print "Waiting for the mission to start ",
world_state = agent_host.getWorldState()
while not world_state.has_mission_begun:
    sys.stdout.write(".")
    time.sleep(0.1)
    world_state = agent_host.getWorldState()
    for error in world_state.errors:
        print "Error:",error.text

print
print "Mission running ",

agent_host.sendCommand("move -1");
time.sleep(0.7);
agent_host.sendCommand("move 0");
agent_host.sendCommand("hotbar.0 1")
agent_host.sendCommand("hotbar.0 0")

time.sleep(0.3);
agent_host.sendCommand("move 0.3")

digDown = True;
attacking = False;
lookStraight = True;
# Loop until mission ends:
while world_state.is_mission_running:
    sys.stdout.write(".")
    time.sleep(0.1)
    world_state = agent_host.getWorldState()
    for error in world_state.errors:
        print "Error:",error.text
    
    if world_state.number_of_observations_since_last_state > 0:
        msg = world_state.observations[-1].text        
        observations = json.loads(msg)
        grid = observations.get(u'cube3x3x3', 0)
        print ["lookStraight ", lookStraight];
        
        if attacking and grid[3]!=u'stone':
            agent_host.sendCommand("attack 0");
            agent_host.sendCommand("move 0.3");
            attacking = False
        if ~attacking and digDown and grid[12] == u'air' and grid[4] == u'stone':
            agent_host.sendCommand("move 0");
            agent_host.sendCommand("pitch 0.2");
            time.sleep(2);
            agent_host.sendCommand("pitch 0");
            agent_host.sendCommand("attack 1");
            digDown = False;
            attacking = True;
            lookStraight = False;
        if ~lookStraight and ~digDown and grid[13] == u'air' and grid[12] != u'air':
            agent_host.sendCommand("pitch -0.15");
            time.sleep(2);
            agent_host.sendCommand("pitch 0");
            lookStraight = True;
        if (grid[12]!=u'air' and grid[12]!=u'grass') :
            agent_host.sendCommand("move 0.7");
            agent_host.sendCommand("attack 1");           
            attacking = True
        
print
print "Mission ended"
# Mission has ended.
