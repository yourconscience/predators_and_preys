import random
import sys
import argparse
import ConfigParser

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
        self.timeToReproduce = reproduceCycle

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
        self.GetData(config)

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
                    self.data[y][x] = Prey(x, y, self.PreyReproduceCycle)
                if self.images['Predator'] == image:
                    self.data[y][x] = Predator(x, y, self.PredatorReproduceCycle,
                                               self.PredatorStarveCycle)

    def GetNeighbors(self, x, y):
        neighbors = []
        for j in range(max(y - 1, 0), min(y + 2, self.height)):
            for i in range(max(x - 1, 0), min(x + 2, self.width)):
                neighbors.append(self.data[j][i])
        return neighbors

    def GetData(self, config):
        parser = ConfigParser.SafeConfigParser()
        parser.read(config)
        self.width = parser.getint('ocean_state', 'width')
        self.height = parser.getint('ocean_state', 'height')
        self.PreyReproduceCycle = parser.getint('prey_params', 'reproduceCycle')
        self.PredatorReproduceCycle = parser.getint('predator_params', 'reproduceCycle')
        self.PredatorStarveCycle = parser.getint('predator_params', 'starveCycle')
        self.data = [['@' for _ in range(self.width)] for _ in range(self.height)]
        if parser.get('ocean_state', 'mode') == 'preset':
            self.ParseInitialState(parser.get('ocean_state', 'field'))

    def Act(self):
        self.processed = [[False for _ in range(self.width)] for _ in range(self.height)]
        for y, line in enumerate(self.data):
            for x, image in enumerate(line):
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

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c','--config', default='config.ini',
                        help='Path to configuration file (default: config.ini)')
    parser.add_argument('-o','--output', default=sys.stdout, type=argparse.FileType('w'),
                        help='Path to output file (default: sys.stdout')
    parser.add_argument('iterations', type=int,
                        help='Number of iterations for process modeling')
    args = parser.parse_args()
    ocean = Ocean(args.config)
    args.output.write(str(ocean))
    for i in range(args.iterations):
        ocean.Act()
        args.output.write(str(ocean))
