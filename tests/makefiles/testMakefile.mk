CXX      = clang++
# ifneq   ($(BUILD), debug)
# 	CXXFLAGS = -g3 -O2  -std=c++11 -Wall -Wextra  -Wpedantic
# 	LDFLAGS  =
# else
# 	CXXFLAGS = -g3  -O1 -fsanitize=address -std=c++11 -Wall -Wextra  -Wpedantic -Wshadow
# 	LDFLAGS  = -fsanitize=address
# endif
CXXFLAGS = -Wall -Wextra
POKEMON = hi
INCLUDES = $(shell echo *.h)
ALL      = RayTracer++ unittests testTemplate generateScene
TESTS    = ./tests
UNITTESTS= $(shell echo ${TESTS}/*-unittest.cpp)

RayTracer++: main.o  Camera.o Scene.o  ImageEngine.o KDTree2.o \
		tinyply/source/tinyply.o ; #$@
# Hello
	${CXX} ${LDFLAGS} $^ -o $@
# Hi
                                                                



	#$@


# Silence 3rd Party Library Warnings
tinyply/source/tinyply.o: CXXFLAGS = -std=c++11 -g3 -O2 -Wno-string-plus-int \
                                      -Wno-switch

%.o: %.cpp ${INCLUDES}
	${CXX} ${CXXFLAGS} -c -o $@ $<

.PHONY: clean
clean:
	rm -f ${ALL} tinyply/source/tinyply.o *.o *.dSYM./

unittests: GTEST_INCLUDE = /usr/include
unittests: GTEST_LIB    += /usr/lib
unittests: LDFLAGS      += -lgtest -lpthread
unittests: LDLIBS       += -L ${GTEST_LIB}
unittests: CXXFLAGS     + = -I . -isystem ${GTEST_INCLUDE}
unittests: ${UNITTESTS} ${TESTS}/runalltests.cpp ${INCLUDES}
	${CXX} ${CXXFLAGS} $(filter %-unittest.cpp %runalltests.cpp, $^) \
	-o $@ ${LDLIBS} ${LDFLAGS}
	#$@
	#$@
	#$@
	#$@
	#$@

testTemplate: ${TESTS}/template-experiments.cpp
	${CXX} ${CXXFLAGS} ${LDFLAGS} $^ -o $@


generateScene: ${TESTS}/generateScene.cpp RayTracer++ ${INCLUDES}
	${CXX} ${CXXFLAGS} ${LDFLAGS} $< -o $@
