cmake_minimum_required(VERSION 3.8)
project(slam_robot_bringup)

find_package(ament_cmake REQUIRED)

# Mostly declarative package: install launch/, config/ and urdf/ into the
# package share directory.
install(
  DIRECTORY launch config urdf
  DESTINATION share/${PROJECT_NAME}
)

# --- Python node: serial_bridge ---
# A single executable script (not an importable module): install it into
# lib/${PROJECT_NAME} so that `ros2 run slam_robot_bringup serial_bridge` can
# find it. RENAME drops the .py extension -> command without the suffix.
# (Use ament_python_install_package for a real importable Python package;
#  here install(PROGRAMS ...) is cleaner.)
install(
  PROGRAMS scripts/serial_bridge.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME serial_bridge
)

ament_package()
