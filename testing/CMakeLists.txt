cmake_minimum_required(VERSION 3.15)

# Set the project name to your project name
project(main C CXX)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_executable(main_app
    ${CMAKE_BINARY_SOURCE_DIR}main.c
)
target_include_directories(main_app PUBLIC ${CMAKE_BINARY_SOURCE_DIR})
