CPPFLAGS=-I/opt/local/include -O6 -Wall
LDFLAGS=-L/opt/local/lib

copymove: LDLIBS += -lfreeimage -lstdc++
copymove: copymove.o
	g++ $(LDFLAGS) copymove.o $(LDLIBS) -o copymove
