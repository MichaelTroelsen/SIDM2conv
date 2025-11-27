# Makefile for sf2export - SF2 to PSID Converter
#
# Build instructions:
#   Windows (MinGW): mingw32-make
#   Windows (MSVC):  nmake /f Makefile.msvc
#   Linux/Mac:       make

# Compiler settings
CXX = g++
CXXFLAGS = -std=c++11 -O2 -Wall -Wextra
TARGET = sf2export.exe

# Source files
SOURCES = sf2export.cpp
OBJECTS = $(SOURCES:.cpp=.o)

# Default target
all: $(TARGET)

# Link
$(TARGET): $(OBJECTS)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(OBJECTS)
	@echo ""
	@echo "Build complete: $(TARGET)"
	@echo "Usage: $(TARGET) input.sf2 output.sid [--driver11|--np20] [-v]"

# Compile
%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

# Clean
clean:
	rm -f $(OBJECTS) $(TARGET)

# Test
test: $(TARGET)
	@echo "Testing sf2export..."
	./$(TARGET) --help || true

.PHONY: all clean test
