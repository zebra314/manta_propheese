all:
	$(MAKE) -C docker all

build:
	$(MAKE) -C docker build

run:
	$(MAKE) -C docker run