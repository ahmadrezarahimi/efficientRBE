# Installing Petrelic on macOS with Apple Silicon

Follow these steps to install the Petrelic library and its dependencies on a macOS system with Apple Silicon (M1 Max).

## 1. Install Xcode Command Line Tools

If you haven't already, install the Xcode Command Line Tools:

```sh
xcode-select --install
```
## 2. Install Homebrew
Install Homebrew, the package manager for macOS:
```sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
## 3. Install Python and other dependencies
Install Python and other required dependencies using Homebrew:
```sh
brew install python3 cmake gmp llvm libb2 openssl
```
Add the Homebrew-installed LLVM to your PATH:
```sh
export PATH="/usr/local/opt/llvm/bin:$PATH"
```
## 5. Compile and install RELIC
Clone the RELIC library repository:
```sh
git clone https://github.com/relic-toolkit/relic.git
```
In your relic folder, create a file named **preset.sh** with the following content:
```sh
#!/bin/sh

export RELIC_LABEL="relic"
export RELIC_CHECK="off"
export RELIC_VERB="off"
export RELIC_FLAGS="-O3 -fomit-frame-pointer -funroll-loops -finline-functions -finline-small-functions -march=native"
export RELIC_CORE="AUTO"
export RELIC_CONF="-DALLOC=AUTO -DWSIZE=64 -DRAND=UDEV -DSHLIB=ON -DSTBIN=OFF -DSTLIB=ON -DSTBIN=OFF -DTESTS=1 -DBENCH=0 -DDEBUG=off -DTRACE=off -DWITH=BN;DV;FP;FPX;EP;EPX;PP;PC;MD"
export RELIC_DOC="off"

```
make **preset.sh** executable:
```sh
chmod +x preset.sh
```
Create a new build directory and change into it:
```sh
mkdir build
cd build
```
Run the **preset.sh** script and build the library:
```sh
../preset.sh ../
cmake ..
make
```
If the build is successful, proceed with installation:
```sh
sudo make install
```

## 5. Compile and install Petrelic
```sh
git clone https://github.com/spring-epfl/petrelic.git
cd petrelic
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install wheel
pip install .
```