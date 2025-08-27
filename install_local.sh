apt update

# Install Pyenv
apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
curl -fsSL https://pyenv.run | bash

# Set up bash environment for Pyenv
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init - bash)"' >> ~/.bashrc
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.profile
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.profile
echo 'eval "$(pyenv init - bash)"' >> ~/.profile

# Reload the shell to apply changes
exec "$SHELL"

# Install Python versions
pyenv install 3.10.18
pyenv global 3.10.18

# Clone openeb
cd ~
git clone https://github.com/prophesee-ai/openeb.git --branch 5.1.1

apt -y install apt-utils build-essential software-properties-common wget unzip curl git cmake
apt -y install libopencv-dev libboost-all-dev libusb-1.0-0-dev libprotobuf-dev protobuf-compiler
apt -y install libhdf5-dev hdf5-tools libglew-dev libglfw3-dev libcanberra-gtk-module ffmpeg

python -m venv ~/prophesee_venv --system-site-packages
source ~/prophesee_venv/bin/activate
export PYTHONNOUSERSITE=true

pip install pip --upgrade
pip install -r ~/openeb/utils/python/requirements_openeb.txt

# Install Pybind11
wget https://github.com/pybind/pybind11/archive/v2.11.0.zip
unzip v2.11.0.zip
cd pybind11-2.11.0
mkdir build && cd build
cmake .. -DPYBIND11_TEST=OFF
cmake --build .
sudo cmake --build . --target install

# Build OpenEB SDK
cd ~/openeb
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF
cmake --build . --config Release -- -j `nproc`
sudo cmake --build . --target install

# Set up udev rules
sudo cp ~/openeb/hal_psee_plugins/resources/rules/*.rules /etc/udev/rules.d
sudo udevadm control --reload-rules
sudo udevadm trigger

source ~/openeb/build/utils/scripts/setup_env.sh
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib
