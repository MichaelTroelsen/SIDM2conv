# Makefile for sf2pack - SF2 Packer with Full Relocation
#
# Build instructions:
#   Windows (MinGW): mingw32-make
#   Linux/Mac:       make

# Compiler settings
CXX = g++
CXXFLAGS = -std=c++11 -O2 -Wall -Wextra
TARGET = sf2pack.exe

# Source files
SOURCES = sf2pack.cpp opcodes.cpp c64memory.cpp packer_simple.cpp psidfile.cpp
OBJECTS = $(SOURCES:.cpp=.o)
HEADERS = opcodes.h c64memory.h packer_simple.h psidfile.h

# Default target
all: $(TARGET)

# Link
$(TARGET): $(OBJECTS)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(OBJECTS)
	@echo ""
	@echo "Build complete: $(TARGET)"
	@echo "Usage: $(TARGET) input.sf2 output.sid [--address ADDR] [--zp ZP] [--title TITLE] [--author AUTHOR] [--copyright COPYRIGHT]"

# Compile
%.o: %.cpp $(HEADERS)
	$(CXX) $(CXXFLAGS) -c $< -o $@

# Clean
clean:
	rm -f $(OBJECTS) $(TARGET)

# Test
test: $(TARGET)
	@echo "Testing sf2pack..."
	./$(TARGET) --help || true

.PHONY: all clean test
