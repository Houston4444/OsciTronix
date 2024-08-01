
PREFIX = /usr/local
DESTDIR = 

LINK = ln -s
LRELEASE ?= lrelease
QT_VERSION ?= 5

APP_NAME := OsciTronix
APP_NAME_LC := oscitronix

# if you set QT_VERSION environment variable to 6 at the make command
# it will choose the other commands QT_API, pyuic6, pylupdate6.
# You will can run oscitronix directly in source without install
# typing: QT_API=PyQt6 python3 src/oscitronix.py

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
BUILD_CFG_FILE := build_config
QT_API_INST := $(shell grep ^QT_API= $(BUILD_CFG_FILE) 2>/dev/null| cut -d'=' -f2)
QT_API_INST ?= PyQt5

ICON_SIZES := 16 24 32 48 64 96 128 256


# ----------------------------------------------------------
# Internationalization

I18N_LANGUAGES :=

all: QT_PREPARE RES UI LOCALE

QT_PREPARE:
	$(info compiling for Qt$(QT_VERSION) using $(QT_API))
	$(file > $(BUILD_CFG_FILE),QT_API=$(QT_API))

    ifeq ($(QT_API), $(QT_API_INST))
    else
		rm -f *~ src/*~ src/*.pyc src/frontend/ui/*.py \
		    resources/locale/*.qm src/resources_rc.py
    endif

RES: src/resources_rc.py

src/resources_rc.py: resources/resources.qrc
	rcc -g python $< |sed 's/ PySide. / qtpy /' > $@

# auto list *.py targets from UI files
UI: $(shell \
	ls resources/ui/*.ui| sed 's|\.ui$$|.py|'| sed 's|^resources/|src/frontend/|')

src/frontend/ui/%.py: resources/ui/%.ui
ifeq ($(PYUIC), pyuic6)
	$(PYUIC) $< > $@
	echo 'import resources_rc' >> $@
else
	$(PYUIC) $< > $@
endif

LOCALE: locale/$(APP_NAME_LC)_en.qm \
		locale/$(APP_NAME_LC)_fr.qm

locale/%.qm: locale/%.ts
	$(LRELEASE) $< -qm $@

clean:
	rm -f *~ src/*~ src/*.pyc src/ui/*.py src/frontend/ui/*.py \
		  resources/locale/*.qm src/resources_rc.py

uninstall:
	# remove icons
	for sz in $(ICON_SIZES);do \
		rm -f $(DESTDIR)$(PREFIX)/share/icons/hicolor/$${sz}x$${sz}/apps/$(APP_NAME_LC).png \
	;done

	# remove source code
	rm -f -R $(DESTDIR)$(PREFIX)/share/$(APP_NAME)

	# remove bin
	rm -f $(DESTDIR)$(PREFIX)/bin/$(APP_NAME_LC)

	# remove desktop file
	rm -f $(DESTDIR)$(PREFIX)/share/applications/$(APP_NAME_LC).desktop

install:
	# install needed directories
	install -d $(DESTDIR)$(PREFIX)/bin/
	install -d $(DESTDIR)$(PREFIX)/share/$(APP_NAME)/locale/


	# Install icons
	for sz in $(ICON_SIZES);do \
		install -d $(DESTDIR)$(PREFIX)/share/icons/hicolor/$${sz}x$${sz}/apps/ ;\
		install -m 644 resources/main_icon/$${sz}x$${sz}/$(APP_NAME_LC).png \
			$(DESTDIR)$(PREFIX)/share/icons/hicolor/$${sz}x$${sz}/apps/ ;\
	done

	# Copy source code
	cp -r src $(DESTDIR)$(PREFIX)/share/$(APP_NAME)/

	#compile source code
	python3 -m compileall $(DESTDIR)$(PREFIX)/share/$(APP_NAME)/src/

	# Install launcher
	install -m 755 data/bin/starter.py \
		$(DESTDIR)$(PREFIX)/bin/$(APP_NAME_LC)

	# modify PREFIX and QT_API in launcher
	sed -i "s?X-PREFIX-X?$(PREFIX)?" \
		$(DESTDIR)$(PREFIX)/bin/$(APP_NAME_LC)
	sed -i "s?X-QT_API-X?$(QT_API_INST)?" \
		$(DESTDIR)$(PREFIX)/bin/$(APP_NAME_LC)

	# install desktop file
	install -m 644 data/share/applications/$(APP_NAME_LC).desktop \
		$(DESTDIR)$(PREFIX)/share/applications/

	# install translations
	install -m 644 locale/*.qm $(DESTDIR)$(PREFIX)/share/$(APP_NAME)/locale/