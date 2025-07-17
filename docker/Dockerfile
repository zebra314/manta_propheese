FROM --platform=$BUILDPLATFORM prophesee/openeb:ubuntu-22.04

# Specify terminal color
ENV TERM=xterm-256color

RUN apt update && apt install -y curl 
RUN apt update && apt install -y git 

# Install zsh
RUN apt-get update && apt-get install -y zsh
RUN chsh -s $(which zsh)

# Install oh-my-zsh
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

# Install p10k
RUN git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k
RUN sed -i 's/ZSH_THEME="robbyrussell"/ZSH_THEME="powerlevel10k\/powerlevel10k"/g' ~/.zshrc
COPY dotfiles/.p10k.zsh /root/.p10k.zsh
COPY dotfiles/.zshrc /root/.zshrc

# Copy gitstatus binary
COPY cachefile/gitstatus /root/.cache/gitstatus

# Install zsh plugins
RUN git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions
RUN git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting
RUN sed -i 's/plugins=(git)/plugins=(git zsh-autosuggestions zsh-syntax-highlighting)/g' ~/.zshrc

# Dependencies for building the SDK
RUN apt update && apt install -y apt-utils
RUN apt update && apt install -y build-essential
RUN apt update && apt install -y software-properties-common 
RUN apt update && apt install -y wget 
RUN apt update && apt install -y unzip 
RUN apt update && apt install -y cmake
RUN apt update && apt install -y libopencv-dev
RUN apt update && apt install -y libboost-all-dev 
RUN apt update && apt install -y libusb-1.0-0-dev 
RUN apt update && apt install -y libprotobuf-dev 
RUN apt update && apt install -y protobuf-compiler
RUN apt update && apt install -y libhdf5-dev 
RUN apt update && apt install -y hdf5-tools 
RUN apt update && apt install -y libglew-dev 
RUN apt update && apt install -y libglfw3-dev 
RUN apt update && apt install -y libcanberra-gtk-module 
RUN apt update && apt install -y ffmpeg
RUN apt update && apt install -y tmux
RUN apt update && apt install -y mesa-utils
RUN apt update && apt install -y usbutils
RUN apt update && apt install -y udev

# Dependencies for test (optional)
# RUN apt update && apt install -y libgtest-dev
# RUN apt update && apt install -y libgmock-dev

# Python
RUN apt update && apt install -y python3.10
RUN ln -s /usr/bin/python3.10 /usr/bin/python

RUN python3 -m venv /opt/prophesee/psee-py3venv --system-site-packages

# Install pip dependencies
COPY requirements_openeb.txt ./openeb_environment/requirements_openeb.txt
RUN /opt/prophesee/psee-py3venv/bin/python3 -m pip install pip --upgrade \
  && /opt/prophesee/psee-py3venv/bin/python3 -m pip install -r openeb_environment/requirements_openeb.txt \
  && rm -rf ~/.cache/pip/*

# Install pybind11 v2.11.0
WORKDIR /opt
RUN wget https://github.com/pybind/pybind11/archive/v2.11.0.zip && \
  unzip v2.11.0.zip && \
  cd pybind11-2.11.0 && \
  mkdir build && cd build && \
  cmake .. -DPYBIND11_TEST=OFF && \
  cmake --build . && \
  cmake --install .

# Build the SDK
RUN export PYTHONNOUSERSITE=true
RUN git clone https://github.com/prophesee-ai/openeb.git --branch 5.1.1
RUN python -m pip install -r openeb/utils/python/requirements_openeb.txt
RUN cd openeb && \
  mkdir build && cd build && \
  cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF -DCOMPILE_PYTHON3_BINDINGS=ON -DPython3_EXECUTABLE=/usr/bin/python3.10 && \
  cmake --build . --config Release -- -j$(nproc) && \
  cmake --build . --target install

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Remove apt cache
RUN rm -rf /var/lib/apt/lists/*

WORKDIR /root/