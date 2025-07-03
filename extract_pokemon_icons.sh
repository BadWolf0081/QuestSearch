#!/bin/bash

INPUT="data/api.json"

awk '
    /<td><img src="pokemon\// {
        # Look back for the previous 7 <td> fields (since the table has many columns)
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
            print "NEW ENTRY: name=" name ", form=" form ", costume=" costume ", img=" img
        }
        delete fields
    }
    { lines[NR] = $0 }
' "$INPUT"