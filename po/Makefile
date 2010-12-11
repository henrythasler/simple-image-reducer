#
# Makefile for the PO files (translation) catalog
#

TOP	 = ../..

# What is this package?
NLSPACKAGE	= simple-image-reducer
POTFILE		= $(NLSPACKAGE).pot
INSTALL		= /usr/bin/install -c
INSTALL_DATA	= $(INSTALL) -m 644
INSTALL_DIR	= /usr/bin/install -d

# destination directory
INSTALL_NLS_DIR = $(DESTDIR)/usr/share/locale

# commands
DIFF		= /usr/bin/diff
GREP		= /bin/grep

# PO catalog handling
MSGMERGE	= msgmerge -v -N
XGETTEXT	= xgettext --default-domain=$(NLSPACKAGE) \
		  --add-comments --from-code=utf-8
MSGFMT		= msgfmt --statistics --verbose

# What do we need to do
POFILES		= $(wildcard *.po)
MOFILES		= $(patsubst %.po,%.mo,$(POFILES))
PYSRC		= $(wildcard ../*.py)
SRCFILES	= $(PYSRC)

all::  update-po $(MOFILES)

po_diff_and_mv_or_rm  = \
	if [ ! -f "$(1)" ] || ($(DIFF) "$(1)" "$(2)" | $(GREP) -v '^. "POT-Creation-Date:' | $(GREP) -q '^[<>] [^\#]'); then \
		echo "Creating/updating $(1)"; \
		mv -f $(2) $(1); \
	else \
		rm -f $(2); \
	fi

po_diff_and_mv_or_rm_func = \
	function po_diff_and_mv_or_rm () { \
		$(call po_diff_and_mv_or_rm,$$1,$$2) \
	}

$(POTFILE): $(SRCFILES)
	$(XGETTEXT) --keyword=_ --keyword=N_ $(SRCFILES)
	@$(call po_diff_and_mv_or_rm,$(POTFILE),$(NLSPACKAGE).po)

update-po: Makefile $(POTFILE) refresh-po

refresh-po: Makefile
	@$(po_diff_and_mv_or_rm_func); \
	for cat in $(POFILES); do \
		lang=`basename $$cat .po`; \
		if $(MSGMERGE) $$lang.po $(POTFILE) > $$lang.pot ; then \
			echo "$(MSGMERGE) of $$lang succeeded" ; \
			po_diff_and_mv_or_rm $$lang.po $$lang.pot; \
		else \
			echo "$(MSGMERGE) of $$lang failed" ; \
			rm -f $$lang.pot ; \
		fi; \
	done

clean:
	@rm -fv *mo *~ .depend

install: $(MOFILES)
	@for n in $(MOFILES); do \
	    l=`basename $$n .mo`; \
	    $(INSTALL_DIR) $(INSTALL_NLS_DIR)/$$l/LC_MESSAGES; \
	    $(INSTALL_DATA) --verbose $$n $(INSTALL_NLS_DIR)/$$l/LC_MESSAGES/$(NLSPACKAGE).mo; \
	done

%.mo: %.po
	$(MSGFMT) -o $@ $<

.PHONY: missing depend


