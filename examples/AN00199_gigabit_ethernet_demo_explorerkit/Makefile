# Do not build for XCOREAI
ifeq ($(XCOREAI),1)
$(error XCOREAI is not supported in this example)
endif

# The TARGET variable determines what target system the application is 
# compiled for. It either refers to an XN file in the source directories
# or a valid argument for the --target option when compiling.

TARGET = XCORE-200-EXPLORER

# The APP_NAME variable determines the name of the final .xe file. It should
# not include the .xe postfix. If left blank the name will default to 
# the project name

APP_NAME =

# The flags passed to xcc when building the application
# You can also set the following to override flags for a particular language:
#
#    XCC_XC_FLAGS, XCC_C_FLAGS, XCC_ASM_FLAGS, XCC_CPP_FLAGS
#
# If the variable XCC_MAP_FLAGS is set it overrides the flags passed to
# xcc for the final link (mapping) stage.

XCC_FLAGS = -g -report -DDEBUG_PRINT_ENABLE -save-temps -Os -Xmapper --map -Xmapper MAPFILE -DRGMII=1

XCC_FLAGS_icmp.xc = $(XCC_FLAGS) -Wno-reinterpret-alignment

# The USED_MODULES variable lists other module used by the application.

USED_MODULES = lib_ethernet(>=4.0.0) lib_otpinfo(>=2.1.0)

#=============================================================================
# The following part of the Makefile includes the common build infrastructure
# for compiling XMOS applications. You should not need to edit below here.

XMOS_MAKE_PATH ?= ../..
include $(XMOS_MAKE_PATH)/xcommon/module_xcommon/build/Makefile.common
