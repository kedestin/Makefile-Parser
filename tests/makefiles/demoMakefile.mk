foo.o: foo.cpp $(shell echo *.h)
        clang++ -Wall -Wextra -c foo.cpp

bar.o: bar.cpp $(shell echo *.h)
        clang++ -Wall -Wextra -c bar.cpp

baz: foo.o bar.o
        clang++ -Wall -Wextra foo.o bar.o