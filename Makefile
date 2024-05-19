
PREFIX = /usr/local
DESTDIR = 

LINK = ln -s
PYUIC ?= pyuic6
PYRCC ?= pyrcc5
PYLUPDATE ?= pylupdate5
LRELEASE ?= lrelease
QT_VERSION ?= 6

# Detect X11 rules dir
ifeq "$(wildcard /etc/X11/Xsession.d/ )" ""
	X11_RC_DIR = $(DESTDIR)/etc/X11/xinit/xinitrc.d/
else
	X11_RC_DIR = $(DESTDIR)/etc/X11/Xsession.d/
endif


# ----------------------------------------------------------
# Internationalization

I18N_LANGUAGES :=

all: RES UI

RES: src/resources_rc.py

src/resources_rc.py: resources/resources.qrc
	$(PYRCC) $< -o $@

UI: tronix_hammer

tronix_hammer: src/ui/main_win.py

src/ui/%.py: resources/ui/%.ui
	$(PYUIC) $< |sed "s/from PyQt$(QT_VERSION) import/from qtpy import/" > $@

clean:
	rm -f *~ src/*~ src/*.pyc src/ui/*.py src/ui_*.py src/resources_rc.py resources/locale/*.qm

install: uninstall pure_install

uninstall:
	echo "uninstall"

pure_install:
	install -d $(DESTDIR)$(PREFIX)/bin/
	install -d $(DESTDIR)$(PREFIX)/share/OsciTronix/

	install -d $(DESTDIR)$(PREFIX)/share/icons/hicolor/16x16/apps/
	install -d $(DESTDIR)$(PREFIX)/share/icons/hicolor/24x24/apps/
	install -d $(DESTDIR)$(PREFIX)/share/icons/hicolor/32x32/apps/
	install -d $(DESTDIR)$(PREFIX)/share/icons/hicolor/48x48/apps/
	install -d $(DESTDIR)$(PREFIX)/share/icons/hicolor/64x64/apps/
	install -d $(DESTDIR)$(PREFIX)/share/icons/hicolor/96x96/apps/
	install -d $(DESTDIR)$(PREFIX)/share/icons/hicolor/128x128/apps/
	install -d $(DESTDIR)$(PREFIX)/share/icons/hicolor/256x256/apps/

	# Install icons
	install -m 644 resources/main_icon/16x16/oscitronix.png   \
		$(DESTDIR)$(PREFIX)/share/icons/hicolor/16x16/apps/
	install -m 644 resources/main_icon/24x24/oscitronix.png   \
		$(DESTDIR)$(PREFIX)/share/icons/hicolor/24x24/apps/
	install -m 644 resources/main_icon/32x32/oscitronix.png   \
		$(DESTDIR)$(PREFIX)/share/icons/hicolor/32x32/apps/
	install -m 644 resources/main_icon/48x48/oscitronix.png   \
		$(DESTDIR)$(PREFIX)/share/icons/hicolor/48x48/apps/
	install -m 644 resources/main_icon/64x64/oscitronix.png   \
		$(DESTDIR)$(PREFIX)/share/icons/hicolor/64x64/apps/
	install -m 644 resources/main_icon/96x96/oscitronix.png   \
		$(DESTDIR)$(PREFIX)/share/icons/hicolor/96x96/apps/
	install -m 644 resources/main_icon/128x128/oscitronix.png \
		$(DESTDIR)$(PREFIX)/share/icons/hicolor/128x128/apps/
	install -m 644 resources/main_icon/256x256/oscitronix.png \
		$(DESTDIR)$(PREFIX)/share/icons/hicolor/256x256/apps/

	# Install bin
	install -m 755 data/bin/oscitronix \
		$(DESTDIR)$(PREFIX)/bin/oscitronix

	# Copy source code
	cp -r src $(DESTDIR)$(PREFIX)/share/OsciTronix/

	# modify PREFIX in main bash scripts
	sed -i "s?X-PREFIX-X?$(PREFIX)?" \
		$(DESTDIR)$(PREFIX)/bin/oscitronix