# pyinstaller --onefile \
#  --name scheduler \
#  --paths src \
#  --add-data "src/scheduler/schedule.toml:." \
#  src/scheduler/cli.py

#pyi-makespec --onefile --name scheduler.exe --paths src  --add-data "..\src\scheduler\scheduler.toml;." src/scheduler/cli.py
#pyinstaller scheduler.spec

./pybuild \
  --onefile \
  --noupx \
  --name scheduler.exe \
  --paths src  \
  --add-data "..\src\scheduler\scheduler.toml;." \
  --collect-all numpy \
  --collect-binaries numpy \
  --collect-all pandas \
  --collect-all ortools \
  --collect-submodules yaml \
    src/scheduler/cli.py
