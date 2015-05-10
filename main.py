import random
import sys
import os
import time
import argparse
import ConfigParser

DISCRETE_TIME = False

class Cell(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def Act(self, ocean):
        return self

class EmptyCell(Cell):
    image = ' '
    def __init__(self, x, y):
        super(EmptyCell, self).__init__(x, y)

class Obstacle(Cell):
    image = '*'
    def __init__(self, x, y):
        super(Obstacle, self).__init__(x, y)

class Creature(EmptyCell):
    def __init__(self, x, y, reproduceCycle):
        super(Creature, self).__init__(x, y)
        self.reproduceCycle = reproduceCycle
        if DISCRETE_TIME:
            self.timeToReproduce = reproduceCycle
        else:
            self.timeToReproduce = random.randrange(reproduceCycle) + 1


    def ChooseNeighbor(self, neighbors, neighborType=EmptyCell):
        selectedNeighbors = filter(lambda x: type(x) == neighborType, neighbors)
        if len(selectedNeighbors) != 0:
            choice = selectedNeighbors[random.randrange(len(selectedNeighbors))]
            return choice
        return None

    def Move(self, ocean):
        target = self.ChooseNeighbor(ocean.GetNeighbors(self.x, self.y))
        if target != None:
            ocean.data[self.y][self.x] = EmptyCell(self.x, self.y)
            self.x = target.x
            self.y = target.y
            ocean.processed[self.y][self.x] = True

    def Reproduce(self, ocean):
        pass

    def Die(self, ocean):
        ocean.data[self.y][self.x] = EmptyCell(self.x, self.y)


class Prey(Creature):
    image = 'O'
    def __init__(self, x, y, reproduceCycle):
        super(Prey, self).__init__(x, y, reproduceCycle)

    def Reproduce(self, ocean):
        target = self.ChooseNeighbor(ocean.GetNeighbors(self.x, self.y))
        if target != None:
            ocean.data[target.y][target.x] = Prey(target.x, target.y, self.reproduceCycle)
            ocean.processed[target.y][target.x] = True

    def Act(self, ocean):
        if self.timeToReproduce == 0:
            # What time is it? Reproduce time!
            self.Reproduce(ocean)
            self.timeToReproduce = self.reproduceCycle
        else:
            self.timeToReproduce -= 1
            self.Move(ocean)
        ocean.data[self.y][self.x] = self

class Predator(Creature):
    image = 'X'
    def __init__(self, x, y, reproduceCycle, starveCycle):
        super(Predator, self).__init__(x, y, reproduceCycle)
        self.starveCycle = starveCycle
        self.timeToStarve = starveCycle

    def Reproduce(self, ocean):
        target = self.ChooseNeighbor(ocean.GetNeighbors(self.x, self.y))
        if target != None:
            ocean.data[target.y][target.x] = Predator(target.x, target.y,
                                                      self.reproduceCycle, self.starveCycle)
            ocean.processed[target.y][target.x] = True

    def Hunt(self, ocean):
        target = self.ChooseNeighbor(ocean.GetNeighbors(self.x, self.y), neighborType=Prey)
        if target != None:
            target.Die(ocean)
            self.timeToStarve = self.starveCycle

    def Act(self, ocean):
        if self.timeToStarve == 0:
            self.Die(ocean)
        else:
            self.timeToStarve -= 1
            if self.timeToReproduce == 0:
                self.Reproduce(ocean)
                self.timeToReproduce = self.reproduceCycle
            else:
                self.timeToReproduce -= 1
                if self.Hunt(ocean) == None:
                    self.Move(ocean)
                else:
                    pass
            ocean.data[self.y][self.x] = self


class Ocean(object):

    def __init__(self, config):
        self.images = {'Empty' : ' ', 'Obstacle' : '*', 'Prey' : 'O', 'Predator' : 'X'}
        self.ParseData(config)

    def ParseInitialState(self, field):
        field = field[1:].split('\n')
        for y, line in enumerate(field):
            for x, image in enumerate(line):
                if not(image in self.images.values()):
                    raise ValueError('Incorrect initial state')
                if self.images['Empty'] == image:
                    self.data[y][x] = EmptyCell(x, y)
                if self.images['Obstacle'] == image:
                    self.data[y][x] = Obstacle(x, y)
                if self.images['Prey'] == image:
                    self.data[y][x] = Prey(x, y, self.preyReproduceCycle)
                if self.images['Predator'] == image:
                    self.data[y][x] = Predator(x, y, self.predatorReproduceCycle,
                                               self.predatorStarveCycle)

    def GenerateRandomState(self, obstacleProb, preyProb, predatorProb):
        for y in range(self.height):
            for x in range(self.width):
                choice = random.uniform(0, 1)
                if choice < obstacleProb:
                    self.data[y][x] = Obstacle(x, y)
                elif choice - obstacleProb < preyProb:
                    self.data[y][x] = Prey(x, y, self.preyReproduceCycle)
                elif choice - obstacleProb - preyProb < predatorProb:
                    self.data[y][x] = Predator(x, y, self.predatorReproduceCycle,
                                               self.predatorStarveCycle)
                else:
                    self.data[y][x] = EmptyCell(x, y)

    def GetNeighbors(self, x, y):
        neighbors = []
        for j in range(max(y - 1, 0), min(y + 2, self.height)):
            for i in range(max(x - 1, 0), min(x + 2, self.width)):
                neighbors.append(self.data[j][i])
        return neighbors

    def NumOfPreys(self):
        return sum(sum(1 for cell in line if type(cell) == Prey) for line in self.data)

    def NumOfPredators(self):
        return sum(sum(1 for cell in line if type(cell) == Predator) for line in self.data)

    def ParseData(self, config):
        parser = ConfigParser.SafeConfigParser()
        parser.read(config)
        self.width = parser.getint('ocean_state', 'width')
        self.height = parser.getint('ocean_state', 'height')
        self.preyReproduceCycle = parser.getint('prey_params', 'reproduceCycle')
        self.predatorReproduceCycle = parser.getint('predator_params', 'reproduceCycle')
        self.predatorStarveCycle = parser.getint('predator_params', 'starveCycle')
        self.data = [['@' for _ in range(self.width)] for _ in range(self.height)]
        if parser.get('ocean_state', 'mode') == 'preset':
            self.ParseInitialState(parser.get('ocean_state', 'field'))
        elif parser.get('ocean_state', 'mode') == 'random':
            self.GenerateRandomState(parser.getfloat('ocean_state', 'obstacleProbability'),
                                     parser.getfloat('ocean_state', 'preyProbability'),
                                     parser.getfloat('ocean_state', 'predatorProbability'))
        else:
            assert ValueError('Incorrect ocean state mode')

    def Act(self):
        self.processed = [[False for _ in range(self.width)] for _ in range(self.height)]
        for y in range(self.height):
            for x in range(self.width):
                if not(self.processed[y][x]):
                    self.processed[y][x] = True
                    self.data[y][x].Act(self)

    def __str__(self):
        field = []
        for y, line in enumerate(self.data):
            images = []
            for x, image in enumerate(line):
                images.append(self.data[y][x].image)
            field.append(''.join(images))
        return '\n'.join(field) + '\n'


def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('iterations', type=int,
                        help='Number of iterations for process modeling.')
    parser.add_argument('-c','--config', default='config.ini',
                        help='Path to configuration file (default: config.ini).')
    parser.add_argument('-d', '--discrete', action='store_true', default=False,
                        help='Time of reproduce and starve are dicrete.')
    parser.add_argument('-r', '--randomSeed', type=int, default=None,
                        help='Used for fields generated randomly.')
    parser.add_argument('-s', '--stats', action='store_true', default=False,
                        help='Calculate stats and make plots of population, if on.')
    args = parser.parse_args()
    return args

def simulate(args):
    ocean = Ocean(args.config)
    sys.stdout.write(str(ocean))
    for turn in range(args.iterations):
        ocean.Act()
        os.system('clear')
        sys.stdout.write('Turn {}. Preys: {}, predators: {}\n'.format(turn,
                                                                      ocean.NumOfPreys(),
                                                                      ocean.NumOfPredators()))
        sys.stdout.write(str(ocean))
        time.sleep(0.00001)

def makeReport(args):
    ocean = Ocean(args.config)
    preys, predators = [], []
    for i in range(args.iterations):
        ocean.Act()
        preys.append(ocean.NumOfPreys())
        predators.append(ocean.NumOfPredators())


if __name__ == '__main__':
    args = parseArgs()
    DISCRETE_TIME = args.discrete
    random.seed(args.randomSeed)
    if args.stats:
        makeReport(args)
    else:
        simulate(args)
