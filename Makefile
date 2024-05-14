
PREFIX = /usr/local
DESTDIR = 

LINK = ln -s
PYUIC ?= pyuic6
PYRCC ?= pyrcc6
PYLUPDATE ?= pylupdate5
LRELEASE ?= lrelease

# Detect X11 rules dir
ifeq "$(wildcard /etc/X11/Xsession.d/ )" ""
	X11_RC_DIR = $(DESTDIR)/etc/X11/xinit/xinitrc.d/
else
	X11_RC_DIR = $(DESTDIR)/etc/X11/Xsession.d/
endif

# -----------------------------------------------------------------------------------------------------------------------------------------
# Internationalization

I18N_LANGUAGES :=

all: RES UI

RES: src/resources_rc.py

src/resources_rc.py: resources/resources.qrc
	$(PYRCC) $< -o $@

UI: tronix_hammer

tronix_hammer: src/ui/main_win.py

src/ui/%.py: resources/ui/%.ui
	$(PYUIC) $< -o $@

clean:
	rm -f *~ src/*~ src/*.pyc src/ui/*.py src/ui_*.py src/resources_rc.py resources/locale/*.qm

