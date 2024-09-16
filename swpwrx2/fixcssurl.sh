#!/bin/bash
if [ $# -ne 1 ]; 
    then echo "wrong number of parameters. must specify the css filename to edit."
fi
sed -i.bak -e 's#url(/swpwr/assets#url(/static/xblock/resources/swpwrx2/public/assets#g' public/$1
