
PREFIX = /usr/local
DESTDIR = 

LINK = ln -s
LRELEASE ?= lrelease
QT_VERSION ?= 5

# if you set QT_VERSION environment variable to 6 at the make command
#  it will choose the other commands QT_API, pyuic6, pylupdate6.
ifeq ($(QT_VERSION), 6)
	QT_API ?= PyQt6
	PYUIC ?= pyuic6
	PYLUPDATE ?= pylupdate6
	ifeq (, $(shell which $(LRELEASE)))
		LRELEASE := lrelease-qt6
	endif
else
    QT_API ?= PyQt5
	PYUIC ?= pyuic5
	PYLUPDATE ?= pylupdate5
	ifeq (, $(shell which $(LRELEASE)))
		LRELEASE := lrelease-qt5
	endif
endif

# neeeded for make install
QT_API_FILE := qt_api.txt
QT_API_INST := $(file < $(QT_API_FILE))
QT_API_INST ?= PyQt5

# ----------------------------------------------------------
# Internationalization

I18N_LANGUAGES :=

all: QT_PREPARE RES UI

QT_PREPARE:
	$(info compiling for Qt$(QT_VERSION) using $(QT_API))
	$(file > $(QT_API_FILE),$(QT_API))

RES: src/resources_rc.py

src/resources_rc.py: resources/resources.qrc
	rcc -g python $< |sed 's/ PySide. / qtpy /' > $@

UI: src/frontend/ui/main_win.py \
	src/frontend/ui/about_oscitronix.py \
	src/frontend/ui/full_amp_import.py \
	src/frontend/ui/local_program.py

src/frontend/ui/%.py: resources/ui/%.ui
	$(PYUIC) $< > $@

clean:
	rm -f *~ src/*~ src/*.pyc src/ui/*.py src/frontend/ui/*.py \
		  resources/locale/*.qm src/resources_rc.py

install: uninstall pure_install

uninstall:
	echo uninstall

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
	sed -i "s?X-QT_API-X?$(QT_API_INST)?" \
		$(DESTDIR)$(PREFIX)/bin/oscitronix
	
	
