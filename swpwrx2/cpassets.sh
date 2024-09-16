#!/bin/bash
#
# version for loading the full swpwr app assets for SBIR Phase 2
#

# Full pathnames to the swpwr build and public directories
x=swpwr
# i=~/src/$x
i=~/$x
b=$i/dist/assets
p=$i/public
s=$i/src
d=$i/dist
m=$d/models

if [ ! -d "dist" ]; then
  mkdir dist
fi
if [ ! -d "dist/assets" ]; then
  mkdir dist/assets
fi

if [ ! -d "public" ]; then
  mkdir public
fi

if [ ! -d "public/assets" ]; then
  mkdir public/assets
fi

if [ ! -d "public/models" ]; then
  mkdir public/models
fi

if [ ! -d "public/BabyFox" ]; then
  mkdir public/BabyFox
fi

# Which precache manifest to copy
# c=precache-manifest.8c5268b68a90c8397a5eb1681f40011c.js

# Copy the swpwr .js .css and .woff2 files to public in swpwrx2
ls $b | grep '\.js$' | sed -e "s#^#cp $b/#" -e 's#$# public/#' | sh
ls $b | grep '\.css$' | sed -e "s#^#cp $b/#" -e 's#$# public/#' | sh
ls $b | grep '\.woff2$' | sed -e "s#^#cp $b/#" -e 's#$# public/assets/#' | sh

# exit

# Which asset javascript files to copy.  Use the most recent one.
js1=`ls -t $b/*.js | sed -e 's#^.*/##g' | head -1`
# echo js1=$js1
# js1=index-xQGfimpM.js

# Which asset css files to copy.  Use the most recent one.
cs1=`ls -t $b/*.css | sed -e 's#^.*/##g' | head -1`
# cs1=index-BlBmDmqs.css
# echo cs1=$cs1

cp $p/android-chrome-192x192.png public/
cp $p/android-chrome-512x512.png public/
cp $p/apple-touch-icon.png public/
cp $p/favicon-16x16.png public/
cp $p/favicon-32x32.png public/
cp $p/favicon.ico public/
cp $p/vite.svg public/
#
cp $d/site.webmanifest public/
#
cp $m/foxy.glb public/models/
cp $p/BabyFox.svg public/BabyFox.svg
cp $p/BabyFox/BabyFox.svg public/BabyFox/BabyFox.svg
#
cp $i/index.html public/
sed -I -e 's#/src/main.tsx#/public/main.tsx#' public/index.html
sed -I -e 's#gltfUrl: "/models/"#gltfUrl: "https://s3.amazonaws.com/stepwise-editorial.querium.com/swpwr/dist/models/"#' public/index.html
# cp $s/App.tsx public/
# cp $s/App.css public/
# cp $s/Stage.tsx public/
# cp $s/main.tsx public/
cp $s/assets/react.svg public/
# cp $s/models/foxy/model.tsx public/
#
cp $b/${js1} public/
#
cp $b/${cs1} public/

# Remember swpwr version info
v=`grep '^  "version":' $i/package.json | sed -e 's/,//' -e 's/^/{/' -e 's/$/}/'`
echo "$v" > public/swpwr_version.json

echo "We are incorporating swpwr $v"
echo "The top-level Javascript file is $js1"
echo "The top-level CSS file is $cs1"
echo "Be sure to edit static/html/swpwrx2student.html to update those filenames:"
echo "    <!-- Load main React app filename -->"
echo "    <script type="module" crossorigin src="/static/xblock/resources/swpwrx2/public/${js1}"></script>"
echo "    <link rel="stylesheet" crossorigin href="/static/xblock/resources/swpwrx2/public/${cs1}">"
echo "Also, be sure to run:"
echo "./fixcssurl.sh $cs1"
echo "./fixjsurl.sh $js1"
