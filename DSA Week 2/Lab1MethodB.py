import math

class Polygon:
    def __init__(self, polyName, sideNum, sideUnit):
        self.polyName = str(polyName)
        self.sideNum = int(sideNum)
        self.sideLen = float(sideUnit)

    def area(self):
        raise NotImplementedError("Error")
class EquilateralTriangle(Polygon):
    def area(self):
        return (self.sideLen ** 2) * 0.433
class Square(Polygon):
    def area(self):
        return self.sideLen ** 2
class RegularPentagon(Polygon):
    def area(self):
        return (1/4) * math.sqrt(5 * (5 + 2 * math.sqrt(5))) * self.sideLen**2
class RegularHexagon(Polygon):
    def area(self):
        return ((3 * math.sqrt(3)) / 2) * self.sideLen**2


choice = int(input("""What polygon?
1 - Equilateral Triangle
2 - Square
3 - Regular Pentagon
4 - Regular Hexagon
> """))

polygonOptions = {
    1: ("Equilateral Triangle", 3, EquilateralTriangle),
    2: ("Square", 4, Square),
    3: ("Regular Pentagon", 5, RegularPentagon),
    4: ("Regular Hexagon", 6, RegularHexagon)
}

if choice in polygonOptions:
    name, sideNum, PolygonClass = polygonOptions[choice]
    side = float(input(f"""
---{name}---
Input the unit of sides: """))
    polygon = PolygonClass(name, sideNum, side)
    print(f"Polygon: {polygon.polyName}\n"
          f"Sides: {sideNum}\n"
          f"Area: {round(polygon.area(), 2)} units²")
