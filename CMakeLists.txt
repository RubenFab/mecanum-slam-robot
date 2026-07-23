cmake_minimum_required(VERSION 3.8)
project(slam_robot_bringup)

find_package(ament_cmake REQUIRED)

# Package majoritairement déclaratif : on installe launch/, config/ et urdf/
# dans le share du package.
install(
  DIRECTORY launch config urdf
  DESTINATION share/${PROJECT_NAME}
)

# --- Nœud Python : serial_bridge ---
# Un seul script exécutable (pas un module importable) : on l'installe dans
# lib/${PROJECT_NAME} pour que `ros2 run slam_robot_bringup serial_bridge` le
# trouve. RENAME supprime l'extension .py -> commande sans le suffixe.
# (On garde ament_python_install_package pour un vrai package Python
#  importable ; ici install(PROGRAMS ...) est plus propre.)
install(
  PROGRAMS scripts/serial_bridge.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME serial_bridge
)

ament_package()
