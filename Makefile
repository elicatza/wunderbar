PROGRAMNAME=wunderbar.py
PREFIX=/usr/local
INSTALL_PATH=$(PREFIX)/bin


install:
	chmod 755 $(PROGRAMNAME)
	mkdir -p $(INSTALL_PATH)
	cp $(PROGRAMNAME) $(INSTALL_PATH)/$(PROGRAMNAME)

uninstall:
	rm -f $(INSTALL_PATH)/$(PROGRAMNAME)


.PHONY: install uninstall 
