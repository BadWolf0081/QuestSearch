#!/bin/bash

INPUT="data/api.json"
OUTPUT="pokemon_icons_found.json"

awk '
    BEGIN {
        print "[" > "'"$OUTPUT"'"
        first = 1
    }
    /<td><img src="pokemon\// {
        td_count = 0
        for (i=NR-1; i>0 && td_count<7; i--) {
            if (match(lines[i], /<td>([^<]*)<\/td>/, arr)) {
                fields[7-td_count] = arr[1]
                td_count++
            }
        }
        name = fields[1]
        form = fields[3]
        costume = fields[4]
        img = ""
        if (match($0, /<img src="(pokemon\/[^"]+)"/, arr2)) {
            img = arr2[1]
        }
        if (!(img in seen)) {
            seen[img] = 1
            if (!first) {
                print "," >> "'"$OUTPUT"'"
            }
            first = 0
            printf "  {\"name\": \"%s\", \"form\": \"%s\", \"costume\": \"%s\", \"img\": \"%s\"}", name, form, costume, img >> "'"$OUTPUT"'"
            print "NEW ENTRY: name=" name ", form=" form ", costume=" costume ", img=" img
        }
        delete fields
    }
    { lines[NR] = $0 }
    END {
        print "\n]" >> "'"$OUTPUT"'"
    }
' "$INPUT"