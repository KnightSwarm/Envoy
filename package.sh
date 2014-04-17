VER=$1

cd $(dirname `readlink -f $0 || realpath $0`)

# Clean up
rm -rf build/envoy-client_$VER
rm -rf build/envoy-server_$VER
rm -rf build/envoy-server-panel_$VER
rm -rf build/envoy-server-api_$VER
rm -rf build/envoy-server-component_$VER

# Recreate build directories
mkdir -p build/envoy-client_$VER
mkdir -p build/envoy-server_$VER
mkdir -p build/envoy-server-panel_$VER
mkdir -p build/envoy-server-api_$VER
mkdir -p build/envoy-server-component_$VER

## Step 1: Envoy API server
BUILDROOT=build/envoy-server-api_$VER
SOURCEDIR=build-assets/envoy-server-api

cp -r $SOURCEDIR/root/* $BUILDROOT/
mkdir $BUILDROOT/DEBIAN
sed "s/\$VER/$VER/g" $SOURCEDIR/control > $BUILDROOT/DEBIAN/control
cp $SOURCEDIR/config $BUILDROOT/DEBIAN/
cp $SOURCEDIR/templates $BUILDROOT/DEBIAN/
cp $SOURCEDIR/postinst $BUILDROOT/DEBIAN/

mkdir -p $BUILDROOT/usr/share/doc/envoy
cp src/config.json.example $BUILDROOT/usr/share/doc/envoy/

mkdir -p $BUILDROOT/usr/share/envoy/api
cp -r src/api/public_html/* $BUILDROOT/usr/share/envoy/api/

# Replace the symlink with actual CPHP...
rm $BUILDROOT/usr/share/envoy/api/cphp
mkdir $BUILDROOT/usr/share/envoy/api/cphp
cp -r /usr/share/php/cphp/* $BUILDROOT/usr/share/envoy/api/cphp/

cd build/
dpkg-deb --build envoy-server-api_$VER
cd ../

## Step 2: Envoy panel
BUILDROOT=build/envoy-server-panel_$VER
SOURCEDIR=build-assets/envoy-server-panel

cp -r $SOURCEDIR/root/* $BUILDROOT/
mkdir $BUILDROOT/DEBIAN
sed "s/\$VER/$VER/g" $SOURCEDIR/control > $BUILDROOT/DEBIAN/control
cp $SOURCEDIR/config $BUILDROOT/DEBIAN/
cp $SOURCEDIR/templates $BUILDROOT/DEBIAN/
cp $SOURCEDIR/postinst $BUILDROOT/DEBIAN/

mkdir -p $BUILDROOT/usr/share/doc/envoy
cp src/config.json.example $BUILDROOT/usr/share/doc/envoy/config.json.example.panel

mkdir -p $BUILDROOT/usr/share/envoy/panel
cp -r src/panel/public_html/* $BUILDROOT/usr/share/envoy/panel/

# Replace the CPHP symlink with actual CPHP...
rm $BUILDROOT/usr/share/envoy/panel/cphp
mkdir $BUILDROOT/usr/share/envoy/panel/cphp
cp -r /usr/share/php/cphp/* $BUILDROOT/usr/share/envoy/panel/cphp/

# Replace the CPHP-REST symlink with actual CPHP-REST...
rm $BUILDROOT/usr/share/envoy/panel/cphp-rest
mkdir $BUILDROOT/usr/share/envoy/panel/cphp-rest
cp -r src/api/public_html/cphp-rest/* $BUILDROOT/usr/share/envoy/panel/cphp-rest/

cd build/
dpkg-deb --build envoy-server-panel_$VER
cd ../

## Step 3: Envoy Server (XMPP) Component
