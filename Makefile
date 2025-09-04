all: build run

build:
	docker build -t manta_propheese:latest .

run:
	xhost +local:root
	docker run -it --rm \
		--privileged \
		--net=host \
		--env="DISPLAY" \
		-e XDG_RUNTIME_DIR=/tmp \
		-e QT_X11_NO_MITSHM=1 \
		-v /dev/bus/usb:/dev/bus/usb \
		-v /tmp/.X11-unix:/tmp/.X11-unix:rw \
		--device=/dev/dri \
		--group-add video \
		--mount type=bind,source=$(CURDIR)/assets,target=/root/assets \
		--mount type=bind,source=$(CURDIR)/example,target=/root/example \
		--mount type=bind,source=$(CURDIR)/scripts,target=/root/scripts \
		--mount type=bind,source=$(CURDIR)/src,target=/root/src \
		manta_propheese:latest zsh
	xhost -local:root

source:
	source ~/openeb/build/utils/scripts/setup_env.sh
	source prophesee_venv/bin/activate