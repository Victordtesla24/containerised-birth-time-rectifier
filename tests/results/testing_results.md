16.27 INFO: pip is looking at multiple versions of fastapi to determine which version is compatible with other requirements. This could take a while.
16.27 ERROR: Cannot install -r requirements.txt (line 2) and pydantic==2.0.0 because these package versions have conflicting dependencies.
16.27
16.27 The conflict is caused by:
16.27     The user requested pydantic==2.0.0
16.27     fastapi 0.100.0 depends on pydantic!=1.8, !=1.8.1, !=2.0.0, !=2.0.1, <3.0.0 and >=1.7.4
16.27
16.27 To fix this you could try to:
16.27 1. loosen the range of package versions you've specified
16.27 2. remove package versions to allow pip attempt to solve the dependency conflict
16.27
16.27 ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/latest/topics/dependency-resolution/#dealing-with-dependency-conflicts
16.37
16.37 [notice] A new release of pip is available: 23.2.1 -> 25.0.1
16.37 [notice] To update, run: pip install --upgrade pip
------
failed to solve: process "/bin/sh -c pip install --no-cache-dir -r requirements.txt" did not complete successfully: exit code: 1
venvvicd@Vics-MacBook-Air containerised-birth-time-rectifier % 
