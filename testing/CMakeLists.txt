cmake_minimum_required(VERSION 3.21)

# Set the project name to your project name
project(main C CXX)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_executable(main
    ${CMAKE_CURRENT_SOURCE_DIR}/main.c
)
target_include_directories(main PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

if(EXISTS ${CMAKE_CURRENT_BINARY_DIR}/compile_commands.json)
    file(COPY ${CMAKE_CURRENT_BINARY_DIR}/compile_commands.json DESTINATION ${CMAKE_CURRENT_SOURCE_DIR})
endif()
