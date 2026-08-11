CFLAGS_RAKV = -Iinclude
SRCS = main.c $(wildcard src/*.c)
OBJS = $(SRCS:.c=.obj)
TARGET = rakv8086.exe

all: $(TARGET)

$(TARGET): $(OBJS)
	@printf '\t%s\t%s\n' 'LINK' $@
	@$(CC) $(CFLAGS_RAKV) $(CFLAGS) -o $@ $(OBJS)

%.obj: %.c
	@printf '\t%s\t%s\n' 'CC' $<
	@$(CC) $(CFLAGS_RAKV) $(CFLAGS) -c -o $@ $<

run: dosbox_c/$(TARGET)
	$(DOSBOX) -conf dosbox.conf

dosbox_c/$(TARGET): $(TARGET)
	@cp $< $@

clean:
	rm -f $(OBJS) $(TARGET)

.PHONY: all clean run
