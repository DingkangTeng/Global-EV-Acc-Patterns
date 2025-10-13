import os

PIRIORITY = ["csv", "shp", "xlsx", "geojson"]

def findFiles(root: str) -> list[str]:
    result = []
    # find folder recuresion
    for root, dirs, files in os.walk(root):
        # Find gdb at fist
        findFile = True
        for d in dirs:
            if d.lower().endswith("gdb"):
                result.append(os.path.join(root, d))
                findFile = False
                dirs.clear()
        # Find other files
        if files and findFile:
            for ext in PIRIORITY:
                matchedFiles = [os.path.join(root, f) for f in files if f.lower().endswith(ext)]
                if matchedFiles:
                    result.extend(matchedFiles)
                    break
            # Stop recursion
            dirs.clear()
    
    return result