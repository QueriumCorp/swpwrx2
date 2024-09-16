#!/bin/bash
if [ $# -ne 1 ];
    then echo "wrong number of parameters. must specify the javascript filename to edit."
fi
sed -i.bak -e 's#"/swpwr/models/foxy.glb"#"/static/xblock/resources/swpwrx2/public/models/foxy.glb"#g' public/$1
