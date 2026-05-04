import csv
import os

LEADS_DATA = """Evan,Harmon,2444679294,128 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,26.94,"Primary roof system, soft metals, and ancillary structures",Damage: 26.94%,PRIORITY_2_LIKELY_DAMAGE
Tyler,Jones,4196621564,129 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.73,"Primary roof system, soft metals, and ancillary structures",Damage: 23.73%,PRIORITY_2_LIKELY_DAMAGE
Troy,Meyers,8755605519,130 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,26.06,"Primary roof system, soft metals, and ancillary structures",Damage: 26.06%,PRIORITY_2_LIKELY_DAMAGE
Mike,Alvarado,1700649630,131 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.75,"Primary roof system, soft metals, and ancillary structures",Damage: 23.75%,PRIORITY_2_LIKELY_DAMAGE
Carol,Soto,0632598681,132 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,24.84,"Primary roof system, soft metals, and ancillary structures",Damage: 24.84%,PRIORITY_2_LIKELY_DAMAGE
Mary,Hall MD,7302341328,133 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.73,"Primary roof system, soft metals, and ancillary structures",Damage: 23.73%,PRIORITY_2_LIKELY_DAMAGE
Tamara,Michael,9908512505,134 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,24.33,"Primary roof system, soft metals, and ancillary structures",Damage: 24.33%,PRIORITY_2_LIKELY_DAMAGE
Jose,Lin,6714138404,135 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.78,"Primary roof system, soft metals, and ancillary structures",Damage: 23.78%,PRIORITY_2_LIKELY_DAMAGE
Kelly,Walsh,4658523614,136 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.49,"Primary roof system, soft metals, and ancillary structures",Damage: 23.49%,PRIORITY_2_LIKELY_DAMAGE
Tiffany,Lambert,8092167354,137 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.66,"Primary roof system, soft metals, and ancillary structures",Damage: 23.66%,PRIORITY_2_LIKELY_DAMAGE
David,Cabrera,4055848584,138 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,22.52,"Primary roof system, soft metals, and ancillary structures",Damage: 22.52%,PRIORITY_2_LIKELY_DAMAGE
Matthew,Smith,7089865512,139 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.57,"Primary roof system, soft metals, and ancillary structures",Damage: 23.57%,PRIORITY_2_LIKELY_DAMAGE
Jonathan,Cooper,7859502388,140 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,21.7,"Primary roof system, soft metals, and ancillary structures",Damage: 21.7%,PRIORITY_2_LIKELY_DAMAGE
Gail,Walker,2329041537,141 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.6,"Primary roof system, soft metals, and ancillary structures",Damage: 23.6%,PRIORITY_2_LIKELY_DAMAGE
Tracey,Dunn,9590267538,142 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,21.01,"Primary roof system, soft metals, and ancillary structures",Damage: 21.01%,PRIORITY_2_LIKELY_DAMAGE
Victoria,Davila,5718309996,143 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.53,"Primary roof system, soft metals, and ancillary structures",Damage: 23.53%,PRIORITY_2_LIKELY_DAMAGE
Tammy,Anderson,6377433978,144 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,20.34,"Primary roof system, soft metals, and ancillary structures",Damage: 20.34%,PRIORITY_2_LIKELY_DAMAGE
Tina,Johnson,4451859013,145 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.53,"Primary roof system, soft metals, and ancillary structures",Damage: 23.53%,PRIORITY_2_LIKELY_DAMAGE
Robert,Williams,8186040376,146 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,20.1,"Primary roof system, soft metals, and ancillary structures",Damage: 20.1%,PRIORITY_2_LIKELY_DAMAGE
Catherine,Valentine,5603775238,147 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.53,"Primary roof system, soft metals, and ancillary structures",Damage: 23.53%,PRIORITY_2_LIKELY_DAMAGE
Henry,Carter MD,9850620062,148 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.62,"Primary roof system, soft metals, and ancillary structures",Damage: 19.62%,PRIORITY_2_LIKELY_DAMAGE
Christina,Casey,2249491032,149 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.42,"Primary roof system, soft metals, and ancillary structures",Damage: 23.42%,PRIORITY_2_LIKELY_DAMAGE
Jacob,Jordan,4606737967,150 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.32,"Primary roof system, soft metals, and ancillary structures",Damage: 19.32%,PRIORITY_2_LIKELY_DAMAGE
Michael,Newman,3397613215,151 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.3,"Primary roof system, soft metals, and ancillary structures",Damage: 23.3%,PRIORITY_2_LIKELY_DAMAGE
Ashley,Adkins,5579125523,152 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.14,"Primary roof system, soft metals, and ancillary structures",Damage: 19.14%,PRIORITY_2_LIKELY_DAMAGE
Charles,Thompson,4006680929,153 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.49,"Primary roof system, soft metals, and ancillary structures",Damage: 23.49%,PRIORITY_2_LIKELY_DAMAGE
Mallory,Grimes,6541561875,154 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,24.56,"Primary roof system, soft metals, and ancillary structures",Damage: 24.56%,PRIORITY_2_LIKELY_DAMAGE
Melinda,Mcmillan,8675250869,155 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.39,"Primary roof system, soft metals, and ancillary structures",Damage: 23.39%,PRIORITY_2_LIKELY_DAMAGE
Matthew,Mueller,4470078126,156 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,24.14,"Primary roof system, soft metals, and ancillary structures",Damage: 24.14%,PRIORITY_2_LIKELY_DAMAGE
Janice,Young,6268683069,157 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.4,"Primary roof system, soft metals, and ancillary structures",Damage: 23.4%,PRIORITY_2_LIKELY_DAMAGE
Dr.,Taylor Huff,7658891928,158 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.75,"Primary roof system, soft metals, and ancillary structures",Damage: 23.75%,PRIORITY_2_LIKELY_DAMAGE
Christine,Dorsey,2382756587,159 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.54,"Primary roof system, soft metals, and ancillary structures",Damage: 23.54%,PRIORITY_2_LIKELY_DAMAGE
Meredith,Mccarthy,6856214009,160 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.75,"Primary roof system, soft metals, and ancillary structures",Damage: 23.75%,PRIORITY_2_LIKELY_DAMAGE
Joshua,Harvey,6583607616,161 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.56,"Primary roof system, soft metals, and ancillary structures",Damage: 23.56%,PRIORITY_2_LIKELY_DAMAGE
Andrew,Andrews,2116369043,162 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,16.97,"Primary roof system, soft metals, and ancillary structures",Damage: 16.97%,PRIORITY_2_LIKELY_DAMAGE
Lisa,Turner,4971340139,163 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.59,"Primary roof system, soft metals, and ancillary structures",Damage: 23.59%,PRIORITY_2_LIKELY_DAMAGE
Kenneth,Patel,9014532743,164 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,16.21,"Primary roof system, soft metals, and ancillary structures",Damage: 16.21%,PRIORITY_2_LIKELY_DAMAGE
Steve,Sosa,6490541056,165 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.66,"Primary roof system, soft metals, and ancillary structures",Damage: 23.66%,PRIORITY_2_LIKELY_DAMAGE
Jennifer,Parker,0688857121,166 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,15.39,"Primary roof system, soft metals, and ancillary structures",Damage: 15.39%,PRIORITY_2_LIKELY_DAMAGE
Ashley,Carroll,7375200869,167 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.73,"Primary roof system, soft metals, and ancillary structures",Damage: 23.73%,PRIORITY_2_LIKELY_DAMAGE
Jennifer,Harrison,7120088804,168 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,14.53,"Primary roof system, soft metals, and ancillary structures",Damage: 14.53%,PRIORITY_2_LIKELY_DAMAGE
Tanya,Edwards,7768000285,169 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.66,"Primary roof system, soft metals, and ancillary structures",Damage: 23.66%,PRIORITY_2_LIKELY_DAMAGE
Holly,Lee,1132239910,170 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,13.41,"Primary roof system, soft metals, and ancillary structures",Damage: 13.41%,PRIORITY_2_LIKELY_DAMAGE
Jessica,Taylor,1219057040,171 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.79,"Primary roof system, soft metals, and ancillary structures",Damage: 23.79%,PRIORITY_2_LIKELY_DAMAGE
Anthony,Garcia,3779750155,172 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,12.72,"Primary roof system, soft metals, and ancillary structures",Damage: 12.72%,PRIORITY_2_LIKELY_DAMAGE
Larry,Wagner,7013839347,173 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.93,"Primary roof system, soft metals, and ancillary structures",Damage: 23.93%,PRIORITY_2_LIKELY_DAMAGE
Ashley,Mcdonald,0710843048,174 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,11.48,"Primary roof system, soft metals, and ancillary structures",Damage: 11.48%,PRIORITY_2_LIKELY_DAMAGE
Ryan,Jacobs,7098638796,175 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.97,"Primary roof system, soft metals, and ancillary structures",Damage: 23.97%,PRIORITY_2_LIKELY_DAMAGE
John,Mayer,7228221334,176 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,11.84,"Primary roof system, soft metals, and ancillary structures",Damage: 11.84%,PRIORITY_2_LIKELY_DAMAGE
Jordan,Thomas,4598580134,177 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,24.05,"Primary roof system, soft metals, and ancillary structures",Damage: 24.05%,PRIORITY_2_LIKELY_DAMAGE
Donna,Mcgee,3286472881,178 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,12.06,"Primary roof system, soft metals, and ancillary structures",Damage: 12.06%,PRIORITY_2_LIKELY_DAMAGE
Leon,Kirk,9454536672,179 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.93,"Primary roof system, soft metals, and ancillary structures",Damage: 23.93%,PRIORITY_2_LIKELY_DAMAGE
Whitney,Harper,3780914641,180 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,12.16,"Primary roof system, soft metals, and ancillary structures",Damage: 12.16%,PRIORITY_2_LIKELY_DAMAGE
Jeff,Jones,2199185699,181 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,24.12,"Primary roof system, soft metals, and ancillary structures",Damage: 24.12%,PRIORITY_2_LIKELY_DAMAGE
Rickey,Scott,6885153873,182 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,12.27,"Primary roof system, soft metals, and ancillary structures",Damage: 12.27%,PRIORITY_2_LIKELY_DAMAGE
Crystal,Olson,9614774377,183 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,24.12,"Primary roof system, soft metals, and ancillary structures",Damage: 24.12%,PRIORITY_2_LIKELY_DAMAGE
Tammy,Boyd,0865176430,184 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,12.05,"Primary roof system, soft metals, and ancillary structures",Damage: 12.05%,PRIORITY_2_LIKELY_DAMAGE
Jeffrey,Walton,3199816895,185 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.5,"Primary roof system, soft metals, and ancillary structures",Damage: 19.5%,PRIORITY_2_LIKELY_DAMAGE
Michael,Garza,1246042974,186 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,12.16,"Primary roof system, soft metals, and ancillary structures",Damage: 12.16%,PRIORITY_2_LIKELY_DAMAGE
Randall,Smith,4931842828,187 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.4,"Primary roof system, soft metals, and ancillary structures",Damage: 19.4%,PRIORITY_2_LIKELY_DAMAGE
Linda,Ortiz,8448844012,188 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,12.61,"Primary roof system, soft metals, and ancillary structures",Damage: 12.61%,PRIORITY_2_LIKELY_DAMAGE
Jacob,Jones,3416742036,189 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.37,"Primary roof system, soft metals, and ancillary structures",Damage: 19.37%,PRIORITY_2_LIKELY_DAMAGE
Lori,Tran,7427446025,190 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,13.12,"Primary roof system, soft metals, and ancillary structures",Damage: 13.12%,PRIORITY_2_LIKELY_DAMAGE
Roger,Gonzalez,2167864150,191 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.31,"Primary roof system, soft metals, and ancillary structures",Damage: 19.31%,PRIORITY_2_LIKELY_DAMAGE
Zachary,Fox,3178870567,192 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,13.6,"Primary roof system, soft metals, and ancillary structures",Damage: 13.6%,PRIORITY_2_LIKELY_DAMAGE
Alex,Cameron,3108941375,193 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.28,"Primary roof system, soft metals, and ancillary structures",Damage: 19.28%,PRIORITY_2_LIKELY_DAMAGE
Jennifer,Castro,4397946594,194 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,14.28,"Primary roof system, soft metals, and ancillary structures",Damage: 14.28%,PRIORITY_2_LIKELY_DAMAGE
Valerie,Mitchell,4805084824,195 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.1,"Primary roof system, soft metals, and ancillary structures",Damage: 19.1%,PRIORITY_2_LIKELY_DAMAGE
Zachary,Gilbert,6391217163,196 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,15.23,"Primary roof system, soft metals, and ancillary structures",Damage: 15.23%,PRIORITY_2_LIKELY_DAMAGE
Mr.,Jason Miller,0529352758,197 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.11,"Primary roof system, soft metals, and ancillary structures",Damage: 19.11%,PRIORITY_2_LIKELY_DAMAGE
Rachel,Aguilar MD,7373071033,198 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.01,"Primary roof system, soft metals, and ancillary structures",Damage: 19.01%,PRIORITY_2_LIKELY_DAMAGE
John,Mullen,3530865451,199 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.01,"Primary roof system, soft metals, and ancillary structures",Damage: 19.01%,PRIORITY_2_LIKELY_DAMAGE
Rebecca,Woods,2833942695,200 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,21.55,"Primary roof system, soft metals, and ancillary structures",Damage: 21.55%,PRIORITY_2_LIKELY_DAMAGE
Melissa,Matthews,3235250754,201 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.58,"Primary roof system, soft metals, and ancillary structures",Damage: 23.58%,PRIORITY_2_LIKELY_DAMAGE
David,Coleman,1833477036,202 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,20.74,"Primary roof system, soft metals, and ancillary structures",Damage: 20.74%,PRIORITY_2_LIKELY_DAMAGE
John,Horton,2566868759,203 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,21.98,"Primary roof system, soft metals, and ancillary structures",Damage: 21.98%,PRIORITY_2_LIKELY_DAMAGE
Mrs.,Crystal Anderson,7583214150,204 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,21.79,"Primary roof system, soft metals, and ancillary structures",Damage: 21.79%,PRIORITY_2_LIKELY_DAMAGE
Lauren,Smith,1118726625,205 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,30.91,"Primary roof system, soft metals, and ancillary structures",Damage: 30.91%,PRIORITY_2_LIKELY_DAMAGE
Daniel,Solomon,2942691830,206 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,25.01,"Primary roof system, soft metals, and ancillary structures",Damage: 25.01%,PRIORITY_2_LIKELY_DAMAGE
Chase,Williams,7536750945,207 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,52.41,"Primary roof system, soft metals, and ancillary structures",Damage: 52.41%,PRIORITY_2_LIKELY_DAMAGE
Henry,Nash,8243708020,208 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,22.83,"Primary roof system, soft metals, and ancillary structures",Damage: 22.83%,PRIORITY_2_LIKELY_DAMAGE
Nicole,Sanchez,8650094478,209 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,67.94,"Primary roof system, soft metals, and ancillary structures",Damage: 67.94%,PRIORITY_2_LIKELY_DAMAGE
Gabriel,Patel,5157020119,210 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,21.34,"Primary roof system, soft metals, and ancillary structures",Damage: 21.34%,PRIORITY_2_LIKELY_DAMAGE
Erin,Ramirez,0805426132,211 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,75.47,"Primary roof system, soft metals, and ancillary structures",Damage: 75.47%,PRIORITY_2_LIKELY_DAMAGE
James,Carter,2987541584,212 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,21.68,"Primary roof system, soft metals, and ancillary structures",Damage: 21.68%,PRIORITY_2_LIKELY_DAMAGE
Jesse,Mendoza,6825643646,213 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,80.59,"Primary roof system, soft metals, and ancillary structures",Damage: 80.59%,PRIORITY_1_EMERGENCY
Janet,Tucker,1280444886,214 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,24.96,"Primary roof system, soft metals, and ancillary structures",Damage: 24.96%,PRIORITY_2_LIKELY_DAMAGE
Deborah,Jenkins,1315464003,215 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,82.17,"Primary roof system, soft metals, and ancillary structures",Damage: 82.17%,PRIORITY_1_EMERGENCY
James,Yang,5108168100,216 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,26.42,"Primary roof system, soft metals, and ancillary structures",Damage: 26.42%,PRIORITY_2_LIKELY_DAMAGE
Sarah,Cox,2691191839,217 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,81.25,"Primary roof system, soft metals, and ancillary structures",Damage: 81.25%,PRIORITY_1_EMERGENCY
Benjamin,Lozano,4313475339,218 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,18.78,"Primary roof system, soft metals, and ancillary structures",Damage: 18.78%,PRIORITY_2_LIKELY_DAMAGE
Elizabeth,Moore,8904153236,219 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,82.52,"Primary roof system, soft metals, and ancillary structures",Damage: 82.52%,PRIORITY_1_EMERGENCY
Brandi,Benton,4139175654,220 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,18.71,"Primary roof system, soft metals, and ancillary structures",Damage: 18.71%,PRIORITY_2_LIKELY_DAMAGE
Michael,Rivera,5583138475,221 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,80.63,"Primary roof system, soft metals, and ancillary structures",Damage: 80.63%,PRIORITY_1_EMERGENCY
Sierra,Moore,4767949076,222 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,18.8,"Primary roof system, soft metals, and ancillary structures",Damage: 18.8%,PRIORITY_2_LIKELY_DAMAGE
Samuel,Thompson DDS,4341932610,223 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,80.2,"Primary roof system, soft metals, and ancillary structures",Damage: 80.2%,PRIORITY_1_EMERGENCY
Christina,Evans,5844107609,224 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,18.96,"Primary roof system, soft metals, and ancillary structures",Damage: 18.96%,PRIORITY_2_LIKELY_DAMAGE
Ana,Snyder,2088129187,225 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,80.29,"Primary roof system, soft metals, and ancillary structures",Damage: 80.29%,PRIORITY_1_EMERGENCY
Leon,Cummings,3350368548,226 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.07,"Primary roof system, soft metals, and ancillary structures",Damage: 19.07%,PRIORITY_2_LIKELY_DAMAGE
Courtney,Martin,9794390694,227 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,79.54,"Primary roof system, soft metals, and ancillary structures",Damage: 79.54%,PRIORITY_2_LIKELY_DAMAGE
Denise,Mcgee,0057070402,228 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.15,"Primary roof system, soft metals, and ancillary structures",Damage: 19.15%,PRIORITY_2_LIKELY_DAMAGE
Michael,Castaneda,1229110532,229 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,79.88,"Primary roof system, soft metals, and ancillary structures",Damage: 79.88%,PRIORITY_2_LIKELY_DAMAGE
Jody,Wolfe,6733432307,230 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.15,"Primary roof system, soft metals, and ancillary structures",Damage: 19.15%,PRIORITY_2_LIKELY_DAMAGE
Robert,Mejia,0435602215,231 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,79.78,"Primary roof system, soft metals, and ancillary structures",Damage: 79.78%,PRIORITY_2_LIKELY_DAMAGE
Erin,Gordon,6216798802,232 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.3,"Primary roof system, soft metals, and ancillary structures",Damage: 19.3%,PRIORITY_2_LIKELY_DAMAGE
Alexander,Oconnor,3124857545,233 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,79.66,"Primary roof system, soft metals, and ancillary structures",Damage: 79.66%,PRIORITY_2_LIKELY_DAMAGE
Allison,Green,0047419644,234 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.58,"Primary roof system, soft metals, and ancillary structures",Damage: 19.58%,PRIORITY_2_LIKELY_DAMAGE
Scott,King,2564094368,235 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,79.76,"Primary roof system, soft metals, and ancillary structures",Damage: 79.76%,PRIORITY_2_LIKELY_DAMAGE
Mario,Potter,2939381374,236 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.7,"Primary roof system, soft metals, and ancillary structures",Damage: 19.7%,PRIORITY_2_LIKELY_DAMAGE
James,Baird,2025155648,237 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,79.67,"Primary roof system, soft metals, and ancillary structures",Damage: 79.67%,PRIORITY_2_LIKELY_DAMAGE
Robert,Franklin,1500075567,238 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.71,"Primary roof system, soft metals, and ancillary structures",Damage: 19.71%,PRIORITY_2_LIKELY_DAMAGE
Shelley,Cantu,0530720274,239 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,78.94,"Primary roof system, soft metals, and ancillary structures",Damage: 78.94%,PRIORITY_2_LIKELY_DAMAGE
Jasmine,Stone,7580320934,240 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,19.8,"Primary roof system, soft metals, and ancillary structures",Damage: 19.8%,PRIORITY_2_LIKELY_DAMAGE
Ashley,Cowan,9056192488,241 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,79.38,"Primary roof system, soft metals, and ancillary structures",Damage: 79.38%,PRIORITY_2_LIKELY_DAMAGE
Nathan,Johnson,6490186458,242 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,20.01,"Primary roof system, soft metals, and ancillary structures",Damage: 20.01%,PRIORITY_2_LIKELY_DAMAGE
Victoria,Williams,5784623813,243 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,79.03,"Primary roof system, soft metals, and ancillary structures",Damage: 79.03%,PRIORITY_2_LIKELY_DAMAGE
Todd,Boyer,4323508350,244 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,20.30,"Primary roof system, soft metals, and ancillary structures",Damage: 20.3%,PRIORITY_2_LIKELY_DAMAGE
Lisa,Munoz,5171008614,245 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,78.85,"Primary roof system, soft metals, and ancillary structures",Damage: 78.85%,PRIORITY_2_LIKELY_DAMAGE
Sarah,Hawkins,5572026060,246 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,20.49,"Primary roof system, soft metals, and ancillary structures",Damage: 20.49%,PRIORITY_2_LIKELY_DAMAGE
Elizabeth,Roberts,3570644280,247 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,78.38,"Primary roof system, soft metals, and ancillary structures",Damage: 78.38%,PRIORITY_2_LIKELY_DAMAGE
Aaron,Jones,9200226967,248 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,20.63,"Primary roof system, soft metals, and ancillary structures",Damage: 20.63%,PRIORITY_2_LIKELY_DAMAGE
Brandon,Stevenson,5747367152,249 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,78.72,"Primary roof system, soft metals, and ancillary structures",Damage: 78.72%,PRIORITY_2_LIKELY_DAMAGE
Carl,Haas,2714301859,250 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,20.87,"Primary roof system, soft metals, and ancillary structures",Damage: 20.87%,PRIORITY_2_LIKELY_DAMAGE
Paul,Case,2546185646,251 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,78.58,"Primary roof system, soft metals, and ancillary structures",Damage: 78.58%,PRIORITY_2_LIKELY_DAMAGE
Allen,Murphy,6905583864,252 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,21.12,"Primary roof system, soft metals, and ancillary structures",Damage: 21.12%,PRIORITY_2_LIKELY_DAMAGE
"Dr.,Kenneth Murphy II",2362339006,253 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,78.72,"Primary roof system, soft metals, and ancillary structures",Damage: 78.72%,PRIORITY_2_LIKELY_DAMAGE
Angela,Wright,2584202862,254 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,21.44,"Primary roof system, soft metals, and ancillary structures",Damage: 21.44%,PRIORITY_2_LIKELY_DAMAGE
Jason,Spencer,5195898149,255 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,78.5,"Primary roof system, soft metals, and ancillary structures",Damage: 78.5%,PRIORITY_2_LIKELY_DAMAGE
Kimberly,Taylor,4207154574,256 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,21.75,"Primary roof system, soft metals, and ancillary structures",Damage: 21.75%,PRIORITY_2_LIKELY_DAMAGE
Evan,Cruz,2359450807,257 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,78.54,"Primary roof system, soft metals, and ancillary structures",Damage: 78.54%,PRIORITY_2_LIKELY_DAMAGE
Christina,Clark,7165256154,258 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,21.75,"Primary roof system, soft metals, and ancillary structures",Damage: 21.75%,PRIORITY_2_LIKELY_DAMAGE
Scott,Wang,9550774559,259 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,78.59,"Primary roof system, soft metals, and ancillary structures",Damage: 78.59%,PRIORITY_2_LIKELY_DAMAGE
Crystal,Kelly,9325118253,260 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,21.63,"Primary roof system, soft metals, and ancillary structures",Damage: 21.63%,PRIORITY_2_LIKELY_DAMAGE
Amy,Nichols,6076781574,261 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,78.56,"Primary roof system, soft metals, and ancillary structures",Damage: 78.56%,PRIORITY_2_LIKELY_DAMAGE
Robin,Lynch,1865580918,262 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,21.79,"Primary roof system, soft metals, and ancillary structures",Damage: 21.79%,PRIORITY_2_LIKELY_DAMAGE
Janice,Mitchell,2485060304,263 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,77.94,"Primary roof system, soft metals, and ancillary structures",Damage: 77.94%,PRIORITY_2_LIKELY_DAMAGE
Mary,Hayes,8304626338,264 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,22.0,"Primary roof system, soft metals, and ancillary structures",Damage: 22.0%,PRIORITY_2_LIKELY_DAMAGE
Joseph,Peck,8657527559,265 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,77.73,"Primary roof system, soft metals, and ancillary structures",Damage: 77.73%,PRIORITY_2_LIKELY_DAMAGE
Daniel,Lewis,3544646270,266 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,22.11,"Primary roof system, soft metals, and ancillary structures",Damage: 22.11%,PRIORITY_2_LIKELY_DAMAGE
Mariah,Williams,7795038060,267 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,76.68,"Primary roof system, soft metals, and ancillary structures",Damage: 76.68%,PRIORITY_2_LIKELY_DAMAGE
Timothy,Parrish,0540794034,268 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,22.44,"Primary roof system, soft metals, and ancillary structures",Damage: 22.44%,PRIORITY_2_LIKELY_DAMAGE
Mike,Trevino,3049951330,269 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,75.55,"Primary roof system, soft metals, and ancillary structures",Damage: 75.55%,PRIORITY_2_LIKELY_DAMAGE
Sara,Miller,9443145239,270 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,22.66,"Primary roof system, soft metals, and ancillary structures",Damage: 22.66%,PRIORITY_2_LIKELY_DAMAGE
Nathan,Sanchez,3201844726,271 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,74.51,"Primary roof system, soft metals, and ancillary structures",Damage: 74.51%,PRIORITY_2_LIKELY_DAMAGE
"Mr.,Mark Nguyen DDS",4478719194,272 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,22.89,"Primary roof system, soft metals, and ancillary structures",Damage: 22.89%,PRIORITY_2_LIKELY_DAMAGE
Taylor,Gill,1020625255,273 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,73.87,"Primary roof system, soft metals, and ancillary structures",Damage: 73.87%,PRIORITY_2_LIKELY_DAMAGE
Monica,White,9618115028,274 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,23.24,"Primary roof system, soft metals, and ancillary structures",Damage: 23.24%,PRIORITY_2_LIKELY_DAMAGE
Jessica,Brown,7853897627,275 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,72.63,"Primary roof system, soft metals, and ancillary structures",Damage: 72.63%,PRIORITY_2_LIKELY_DAMAGE
Katherine,Campbell,3006184766,276 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,20.9,"Primary roof system, soft metals, and ancillary structures",Damage: 20.9%,PRIORITY_2_LIKELY_DAMAGE
Anna,Smith,6255916699,277 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,71.88,"Primary roof system, soft metals, and ancillary structures",Damage: 71.88%,PRIORITY_2_LIKELY_DAMAGE
Joyce,Brown,2367284016,278 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,20.66,"Primary roof system, soft metals, and ancillary structures",Damage: 20.66%,PRIORITY_2_LIKELY_DAMAGE
Debra,Barajas,5454211117,279 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,70.38,"Primary roof system, soft metals, and ancillary structures",Damage: 70.38%,PRIORITY_2_LIKELY_DAMAGE
Grant,Lawson,2037128523,280 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,20.56,"Primary roof system, soft metals, and ancillary structures",Damage: 20.56%,PRIORITY_2_LIKELY_DAMAGE
Robert,Flores,4195162442,281 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,69.13,"Primary roof system, soft metals, and ancillary structures",Damage: 69.13%,PRIORITY_2_LIKELY_DAMAGE
Mark,Ortiz,1905849654,282 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,20.54,"Primary roof system, soft metals, and ancillary structures",Damage: 20.54%,PRIORITY_2_LIKELY_DAMAGE
David,Mann,6087987796,283 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,67.44,"Primary roof system, soft metals, and ancillary structures",Damage: 67.44%,PRIORITY_2_LIKELY_DAMAGE
Michele,Mcdaniel,0175676530,284 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,20.49,"Primary roof system, soft metals, and ancillary structures",Damage: 20.49%,PRIORITY_2_LIKELY_DAMAGE
Carolyn,Clayton,2995977377,285 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,65.59,"Primary roof system, soft metals, and ancillary structures",Damage: 65.59%,PRIORITY_2_LIKELY_DAMAGE
Amber,Keller,9107501609,286 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,20.45,"Primary roof system, soft metals, and ancillary structures",Damage: 20.45%,PRIORITY_2_LIKELY_DAMAGE
Thomas,Young,5622287400,287 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,64.31,"Primary roof system, soft metals, and ancillary structures",Damage: 64.31%,PRIORITY_2_LIKELY_DAMAGE
Jennifer,Taylor,3861269352,288 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,20.48,"Primary roof system, soft metals, and ancillary structures",Damage: 20.48%,PRIORITY_2_LIKELY_DAMAGE
Benjamin,Meadows,4072596365,289 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,20.85,"Primary roof system, soft metals, and ancillary structures",Damage: 20.85%,PRIORITY_2_LIKELY_DAMAGE
Sara,Spears,1892674751,290 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,20.28,"Primary roof system, soft metals, and ancillary structures",Damage: 20.28%,PRIORITY_2_LIKELY_DAMAGE
Mark,Watkins,6365946950,291 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,20.6,"Primary roof system, soft metals, and ancillary structures",Damage: 20.6%,PRIORITY_2_LIKELY_DAMAGE
Christine,Griffin,0368427715,292 Indiana Ave,Wichita Falls,TX,76301,2026-04-25,3.0,Hail,20.28,"Primary roof system, soft metals, and ancillary structures",Damage: 20.28%,PRIORITY_2_LIKELY_DAMAGE
"""

OUTPUT_FILE = "leads_manifests/wichita_falls_batch.csv"

def ingest():
    lines = LEADS_DATA.strip().split("\n")
    fieldnames = [
        'first_name', 'last_name', 'phone_number', 'property_address',
        'city', 'state', 'zip_code', 'hail_date', 'hail_size',
        'storm_type', 'damage_probability', 'structures_hit',
        'image_findings', 'lead_priority'
    ]

    count = 0
    with open(OUTPUT_FILE, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for line in lines:
            parts = list(csv.reader([line]))[0]
            if len(parts) >= 14:
                row = dict(zip(fieldnames, parts))
                # Clean phone
                digits = ''.join(filter(str.isdigit, row['phone_number']))
                if len(digits) == 10:
                    row['phone_number'] = f"+1{digits}"
                elif len(digits) == 11 and digits.startswith('1'):
                    row['phone_number'] = f"+{digits}"
                
                # Basic vetting
                if len(row['phone_number']) != 12:
                    continue
                if "DEEP SEARCH" in row['first_name'].upper():
                    continue

                writer.writerow(row)
                count += 1

    print(f"✅ Ingested {count} clean Wichita Falls leads to {OUTPUT_FILE}")

if __name__ == "__main__":
    ingest()
