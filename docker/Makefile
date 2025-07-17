all: build run

build:
	docker build -t propheese:latest .

run:
	xhost +local:root
	docker run -it --rm \
		--name propheese \
		--privileged \
		--net=host \
		-e DISPLAY \
		--env="DISPLAY" \
		-e XDG_RUNTIME_DIR=/tmp \
		-e QT_X11_NO_MITSHM=1 \
		-v /dev/bus/usb:/dev/bus/usb \
		-v /tmp/.X11-unix/:/tmp/.X11-unix/ \
		--mount type=bind,source=$(CURDIR)/../python,target=/root/python \
		propheese:latest zsh
	xhost -local:root