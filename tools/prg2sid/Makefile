#################################################################
## make CFG=Debug  to build debug version
## tested also in MingW/MSYS
#################################################################

ifneq (,$(findstring Debug, $(CFG)))
  override CFG = Debug
else
  override CFG = Release
endif

PROJECT = p2s
CC = gcc

ifeq ($(CFG),Debug)
  OBJ_DIR = Debug
  OUTPUT_DIR = Debug
  TARGET = $(PROJECT)
  C_INCLUDE_DIRS =
  C_PREPROC =
  CFLAGS = -pipe  -Wall -g2 -O0
  RC_INCLUDE_DIRS =
  RC_PREPROC =
  RCFLAGS =
  LIB_DIRS =
  LIBS =
  LDFLAGS = -pipe
endif

ifeq ($(CFG),Release)
  OBJ_DIR = Release
  OUTPUT_DIR = Release
  TARGET = $(PROJECT)
  C_INCLUDE_DIRS =
  C_PREPROC =
  CFLAGS = -pipe  -Wall -g0 -O3
  RC_INCLUDE_DIRS =
  RC_PREPROC =
  RCFLAGS =
  LIB_DIRS =
  LIBS =
  LDFLAGS = -pipe -s
endif

ifeq ($(OS),Windows_NT)
  NULL =
else
  NULL = nul
endif

SRC_OBJS = \
  $(OBJ_DIR)/p2s.o

define build_target
@echo Linking...
@$(CC) -o "$(OUTPUT_DIR)/$(TARGET)" $(SRC_OBJS) $(LIB_DIRS) $(LIBS) $(LDFLAGS)
endef

define compile_source
@echo Compiling $<
@$(CC) $(CFLAGS) $(C_PREPROC) $(C_INCLUDE_DIRS) -c "$<" -o "$@"
endef

.PHONY: print_header directories

$(TARGET): print_header directories $(SRC_OBJS)
	$(build_target)

.PHONY: clean cleanall

cleanall:
	@echo Deleting intermediate files for '$(PROJECT) - $(CFG)'
	-@rm -f $(OBJ_DIR)/*.o
	-@rm -f "$(OUTPUT_DIR)/$(TARGET)"
	-@rmdir "$(OUTPUT_DIR)"

clean:
	@echo Deleting intermediate files for '$(PROJECT) - $(CFG)'
	-@rm -f $(OBJ_DIR)/*.o

print_header:
	@echo ----------Configuration: $(PROJECT) - $(CFG)----------

directories:
	-@mkdir "$(OUTPUT_DIR)"
	-@mkdir "$(OBJ_DIR)"

$(OBJ_DIR)/p2s.o: p2s.c
	$(compile_source)
