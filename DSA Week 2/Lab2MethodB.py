import random

def find_minmax(sequence):
    if len(sequence) == 1:
        return sequence[0], sequence[0]
    else:
        minValue, maxValue = find_minmax(sequence[1:])
        return min(sequence[0], minValue), max(sequence[0], maxValue)

num1 = random.randint(0, 1000)
num2 = random.randint(0, 1000)
num3 = random.randint(0, 1000)
num4 = random.randint(0, 1000)
num5 = random.randint(0, 1000)
numSequence = [num1, num2, num3, num4, num5]

highest, lowest = find_minmax(numSequence)

print("Sequence:", numSequence)
print("Minimum Value:", highest)
print("Maximum Value:", lowest)
