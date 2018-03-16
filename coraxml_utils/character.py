
import re

# replacements needs to be an array, since they must be done in the
# correct order.
#
# first element needs to be a regex, so it must be properly escaped
# second element is the codepoint(s) hexadecimal. it can be more than one, but it must always be codepoints
#                backreferences aren't possible
# third element can be any number of literal characters, but should be ASCII
replacements = [
    # Bonn     |    UTF       | Simple              | Explanation
    # ---------+--------------+---------------------+---------------------------------------------------------

    [ r"\\&99",       "\u25A1",     "{99}"       ], # leeres feld

    # textspezifische sonderzeichen
    # einstellige sonderzeichen muessen am ende kommen, da diese ersetzungen
    # der reihe nach abgearbeitet werden
    [ r"\\&10",       "\u2469",     "{10}"       ],
    [ r"\\&11",       "\u246A",     "{11}"       ],
    [ r"\\&12",       "\u246B",     "{12}"       ],
    [ r"\\&13",       "\u246C",     "{13}"       ],
    [ r"\\&14",       "\u246D",     "{14}"       ],
    [ r"\\&15",       "\u246E",     "{15}"       ],
    [ r"\\&16",       "\u246F",     "{16}"       ],
    [ r"\\&17",       "\u2470",     "{17}"       ],
    [ r"\\&18",       "\u2471",     "{18}"       ],
    [ r"\\&19",       "\u2472",     "{19}"       ],
    [ r"\\&20",       "\u2473",     "{20}"       ],
    [ r"\\&21",       "\u3251",     "{21}"       ],
    [ r"\\&22",       "\u3252",     "{22}"       ],
    [ r"\\&23",       "\u3253",     "{23}"       ],
    [ r"\\&24",       "\u3254",     "{24}"       ],
    [ r"\\&25",       "\u3255",     "{25}"       ],
    [ r"\\&26",       "\u3256",     "{26}"       ],
    [ r"\\&27",       "\u3257",     "{27}"       ],
    [ r"\\&28",       "\u3258",     "{28}"       ],
    [ r"\\&29",       "\u3259",     "{29}"       ],
    [ r"\\&30",       "\u325A",     "{30}"       ],
    [ r"\\&31",       "\u325B",     "{31}"       ],
    [ r"\\&32",       "\u325C",     "{32}"       ],
    [ r"\\&33",       "\u325D",     "{33}"       ],
    [ r"\\&34",       "\u325E",     "{34}"       ],
    [ r"\\&35",       "\u325F",     "{35}"       ],
    [ r"\\&1",       "\u2460",     "{1}"       ],
    [ r"\\&2",       "\u2461",     "{2}"       ],
    [ r"\\&3",       "\u2462",     "{3}"       ],
    [ r"\\&4",       "\u2463",     "{4}"       ],
    [ r"\\&5",       "\u2464",     "{5}"       ],
    [ r"\\&6",       "\u2465",     "{6}"       ],
    [ r"\\&7",       "\u2466",     "{7}"       ],
    [ r"\\&8",       "\u2467",     "{8}"       ],
    [ r"\\&9",       "\u2468",     "{9}"       ],


    [ r"\$",         "\u017F",     "s"         ],      # LATIN SMALL LETTER LONG S
    [ r"\%9",        "\uA770",     "us"        ],      # SUPERSCRIPT US
    [ r"\%2",        "\u1DD1",     "ur"        ],      # SUPERSCRIPT UR

    # Kürzungen mit ampersand + Zahl
    [r"(?<!{)(?<!\\)&3(?!\d)", "\uA76B", "et"  ],      # ABBREV FINAL ET
    [r"(?<!{)(?<!\\)&4(?!\d)", "\uA75D", "rum" ],      # ABBREV SMALL RUM
    [r"(?<!{)(?<!\\)&7(?!\d)", "\uF158", "et"  ],      # geaendert von 204A auf wunsch des anselm projekts
    [r"(?<!{)(?<!\\)&9(?!\d)", "\uA76F", "con" ],      # ABBREV SMALL CON DESCENDING


    # obsolete, see right below
    #[ /\%\%/,       "F1570025", "r%"        ],      # %% = kuerzung r durch superskription des folgevokals
                                                    #    ersetze %% durch '% und modifiziere weiter unten
                                                    #    (0025 = "%")
    # r-Kuerzung durch Hochstellung des Folgevokals
    # superscript, not overscript!
    # most are in phonetic extensions block, except for i
    # which was placed in superscripts and subscripts for lulz
    [ r"%%[aäâáà]",     "\u1D43",     "ra"         ],  # MODIFIER LETTER SMALL A
    [ r"%%[eêéè]",      "\u1D49",     "re"         ],  # MODIFIER LETTER SMALL E
    [ r"%%[iîíì]",      "\u2071",     "ri"         ],  # SUPERSCRIPT LATIN SMALL LETTER I
    [ r"%%[oöôóò]",     "\u1D52",     "ro"         ],  # MODIFIER LETTER SMALL O
    [ r"%%[uüûúù]",     "\u1D58",     "ru"         ],  # MODIFIER LETTER SMALL U
    [ r"%%[v]",         "\u1D5B",     "rv"         ],
    [ r"ct?\%'?(?![.])",    "\u0063\u035B", "cetera"    ],      # cetera kuerzung (0063 - 'c')
    # TODO ^-- simpl?
    [ r"e\\,",       "\u0119",     "e"         ],      # SMALL E WITH OGONEK
    [ r"E\\,",       "\u0118",     "E"         ],      # LATIN CAPITAL E WITH OGONEK

    # r kuerzung
    [ r"(?<=v)'",                  "\u02E2",     "er"        ],      # v' => ver
    [ r"(?<=[äöüaeiouy]r)'",       "\u02E2",     "r"         ],      # r' => rr, falls ein Vokal voransteht
    [ r"r'",                       "\u02E2",     "er"        ],      # r' => er
    [ r"(?<!\\)'(?=r)",            "\u02E2",     "e"         ],      # 'r => er
    [ r"(?<=[äöüaeiouy])'",        "\u02E2",     "r"         ],      # ersetze ' durch r, falls ein Vokal voransteht
    [ r"(?<!\\)'(?=[äöüaeiouy])",  "\u02E2",     "r"         ],      #     "       "         "        "   folgt
    [ r"(?<!\\)'",                 "\u02E2",     "er"        ],      # ersetze ' durch er
    # ^-- quote, but not after \

    # v-- war: E8B1/E8B0 aus MUFI, ab unicode 5.1 in latin supplement d
    [ r"q\\\/",      "\uA759",     "que"       ],      # q\/ que oder qu
    [ r"Q\\\/",      "\uA758",     "Que"       ],
    # v-- p\/ = pro, but no MUFI codepoint exists for this
    #                so they're just replaced by [Pp]
    [ r"p\\\/",      "\u0070",     "pro"       ],
    [ r"P\\\/",      "\u0050",     "Pro"       ],
    # \/ is apparently another abbreviation sign in anselm texts
    # but to my knowledge, there is no single codepoint for this,
    # therefore, it shall be replaced by nothing, and simplifed to
    # dash
    [ r"\\\/",       "",         "-"          ],
    # ----
    [ r"p\\_",       "\uA751",     "per"       ],      # p\_ er, prae
    [ r"P\\_",       "\uA750",     "Per"       ],
    [ r"q_2",        "\uE8B3",     "quia"      ],      # q_2 quia
    [ r"\*C",        "\uF1E1",     "//"        ],      # PARAGRAPHUS (MUFI)
    [ r"·",          "\u00B7",     "."         ],      # middle dot in roman digits
    [ r"\%\.",       "\u00B7",     "."         ],      # middle dot
    [ r"\.\\[7'^]",   "\uF161",    "."         ],      # PUNCTUS ELEVATUS
    [ r"∙",          "\u00B7",     "."         ],      # bullet operator => middle dot

    # middle dot in abbreviations 
    [r"%\.([A-Za-zÄÖÜäöüß$])%\.", "\u00B7\\1\u00B7", r".\1."],

    # combining diacritics
    [ r"\\`",        "\u0300",     ""          ],      # combining grave
    [ r"\\['´]",     "\u0301",     ""          ],      # combining acute
    [ r"\\\^",       "\u0302",     ""          ],      # circumflex
    [ r"\%-",        "\u0304",     "-"         ],      # contraction sign (display like nasal bar)
    # \/ schraegstrich durch unterlaenge - no MUFI codepoint
    [ r"\\_",        "\u0332",     ""          ],      # combining abbreviation mark bar below
    [ r"\\\.",       "\u0307",     ""          ],      # dot above
    [ r"\\:",        "\u0308",     ""          ],      # diaresis (umlaut)

    # nasal bar rules for uppercase letters
    [ r"(?<=^VN)\\-(?=$| )",                   "\u0304",     "D"         ],      # special rule for "vn\-"
    [ r"(?<=[ÄÖÜAEIOUVWY][NM])\\-",      "\u0304",     ""          ],      # Vn\-  => Vn   / Vm\-  => Vm
    [ r"^N\\-",                        "\u006E\u0304", "EN"        ],      # Cn\-  => Cen
    [ r"^M\\-",                       "\u006D\u0304", "EM"        ],      # Cm\-  => Cem
    [ r"(?<=[^ÄÖÜAEIOUVWY])N\\-",        "\u006E\u0304", "EN"        ],      # Cn\-  => Cen
    [ r"(?<=[^ÄÖÜAEIOUVWY])M\\-",        "\u006D\u0304", "EM"        ],      # Cm\-  => Cem
    [ r"(?<=[ÄÖÜAEIOUVWY])\\-(?=[NM])",  "\u0304",     ""          ],      # V\-n  => Vn   / V\-m  => Vm
    [ r"(?<=[ÄÖÜAEIOUVWY])\\-(?![NM])",  "\u0304",     "N"         ],      # V\-   => Vn
    [ r"(?<=[BCDFGHJKLMNPQRSTWXZ])\\-(?=[NM])",  "\u0304",     "E"         ],      # C\-n  => Cen  / C\-m  => Cem
    [ r"(?<=[BCDFGHJKLMNPQRSTWXZ])\\-(?![NM])",  "\u0304",     "EN"        ],      # C\-   => Cen

    # nasal bar
    [ r"(?<=^vn)\\-(?=$| )",                   "\u0304",     "d"         ],      # special rule for "vn\-"
    [ r"(?<=[äöüaeiouvwy][nm])\\-",      "\u0304",     ""          ],      # Vn\-  => Vn   / Vm\-  => Vm
    [ r"^n\\-",        "\u006E\u0304", "en"        ],      # Cn\-  => Cen
    [ r"^m\\-",        "\u006D\u0304", "em"        ],      # Cm\-  => Cem
    [ r"(?<=[^äöüaeiouvwy])n\\-",        "\u006E\u0304", "en"        ],      # Cn\-  => Cen
    [ r"(?<=[^äöüaeiouvwy])m\\-",        "\u006D\u0304", "em"        ],      # Cm\-  => Cem
    [ r"(?<=[äöüaeiouvwy])\\-(?=[nm])",  "\u0304",     ""          ],      # V\-n  => Vn   / V\-m  => Vm
    [ r"(?<=[äöüaeiouvwy])\\-(?![nm])",  "\u0304",     "n"         ],      # V\-   => Vn
    [ r"(?<![äöüaeiouvwy])\\-(?=[nm])",  "\u0304",     "e"         ],      # C\-n  => Cen  / C\-m  => Cem
    [ r"(?<![äöüaeiouvwy])\\-(?![nm])",  "\u0304",     "en"        ],      # C\-   => Cen
    # old rule:         [ r"\\-",        "0304",     "n"         ],      # macron (nasal bar)

    # d_e ligature, frequent in REM
    [ r"d_e",        "\u0064\u1D49",     "de" ],
    # x_y - ligature, but not for all ligatures exist codepoints. solution: replace by ZERO WITH JOINER
    [ r"_",          "\u200D",     ""          ],

    # ordinary letters superposed: \a or %a
    [ r"[\\%][aäâáà]",     "\u0363",     "a"         ],
    [ r"[\\%][eêéè]",     "\u0364",     "e"         ],
    [ r"[\\%][iîíì]",     "\u0365",     "i"         ],
    [ r"[\\%][oöôóò]",     "\u0366",     "o"         ],
    [ r"[\\%][uüûúù]",     "\u0367",     "u"         ],

    [ r"[\\%]c",     "\u0368",     "c"         ],
    [ r"[\\%]d",     "\u0369",     "d"         ],
    [ r"[\\%]h",     "\u036A",     "h"         ],
    [ r"[\\%]m",     "\u036B",     "m"         ],
    [ r"[\\%]r",     "\u036C",     "r"         ],
    [ r"[\\%]t",     "\u036D",     "t"         ],
    [ r"[\\%]v",     "\u036E",     "v"         ],
    [ r"[\\%]x",     "\u036F",     "x"         ],

    # superposed letter not readable: \* -> half ring
    [ r"\\\*",       "\u0357",     ""          ],      # COMBINING HALF RING ABOVE

    # supplement
    [ r"[\\%]g",     "\u1DDA",     "g"         ],
    [ r"[\\%]k",     "\u1DDC",     "k"         ],
    [ r"[\\%]l",     "\u1DDD",     "l"         ],
    [ r"[\\%]n",     "\u1DE0",     "n"         ],
    [ r"[\\%]r",     "\u1DE2",     "r"         ],
    [ r"[\\%]s",     "\u1DE4",     "s"         ],
    [ r"[\\%]z",     "\u1DE6",     "z"         ],

    # still missing from official unicode
    # -> currently private use area
    # http://skaldic.arts.usyd.edu.au/db.php?table=mufi_char&if=mufi&cp=00
    [ r"[\\%]b",     "\uF012",     "b"         ],
    [ r"[\\%]f",     "\uF017",     "f"         ],
    [ r"[\\%]p",     "\uF025",     "p"         ],
    [ r"[\\%][yý]",     "\uF02B",     "y"         ],
    [ r"[\\%]j",     "\uF030",     "j"         ],
    [ r"[\\%]q",     "\uF033",     "q"         ],
    [ r"[\\%]w",     "\uF03C",     "w"         ],

    # values below are just for simple forms, therefore the second column
    # is equivalent to the first
    [ r"â",          "\u00E2",     "a"         ],
    [ r"ê",          "\u00EA",     "e"         ],
    [ r"î",          "\u00EE",     "i"         ],
    [ r"ô",          "\u00F4",     "o"         ],
    [ r"û",          "\u00FB",     "u"         ],

    [ r"Â",          "\u00C2",     "A"         ],
    [ r"Ê",          "\u00CA",     "E"         ],
    [ r"Î",          "\u00CE",     "I"         ],
    [ r"Ô",          "\u00D4",     "O"         ],
    [ r"Û",          "\u00DB",     "U"         ],

    # acute
    [ r"á",          "\u00E1",     "a"         ],
    [ r"é",          "\u00E9",     "e"         ],
    [ r"í",          "\u00ED",     "i"         ],
    [ r"ó",          "\u00F3",     "o"         ],
    [ r"ú",          "\u00FA",     "u"         ],
    [ r"ý",          "\u00FD",     "y"         ],

    [ r"Á",          "\u00C1",     "A"         ],
    [ r"É",          "\u00C9",     "E"         ],
    [ r"Í",          "\u00CD",     "I"         ],
    [ r"Ó",          "\u00D3",     "O"         ],
    [ r"Ú",          "\u00DA",     "U"         ],
    [ r"Ý",          "\u00DD",     "Y"         ],

    # gravis
    [ r"à",          "\u00E0",     "a"         ],
    [ r"è",          "\u00E8",     "e"         ],
    [ r"ì",          "\u00EC",     "i"         ],
    [ r"ò",          "\u00F2",     "o"         ],
    [ r"ù",          "\u00F9",     "u"         ],

    [ r"À",          "\u00C0",     "A"         ],
    [ r"È",          "\u00C8",     "E"         ],
    [ r"Ì",          "\u00CC",     "I"         ],
    [ r"Ò",          "\u00D2",     "O"         ],
    [ r"Ù",          "\u00D9",     "U"         ],

    # ligatures et al
    [ r"æ",          "\u00E6",     "ae"        ],
    [ r"Æ",          "\u00C6",     "Ae"        ],
    [ r"&&",         "\u0026",     "und"       ],

 
]



class Char:

    def __init__(self, _trans, dipl_utf="", anno_utf="", anno_simple=""):
        self.string = _trans
        self.dipl_utf = dipl_utf
        self.anno_utf = anno_utf
        self.anno_simple = anno_simple
        self.anno_bound = False
        self.dipl_bound = False
        self.line_break = False

    def __str__(self):
        return "{0}({1})".format(self.__class__.__name__, self.string)

    def __eq__(self, obj):

        if not isinstance(obj, self.__class__):
            return False
        else:
            return (
                self.string == obj.string and
                self.dipl_utf == obj.dipl_utf and
                self.anno_utf == obj.anno_utf and
                self.anno_simple == obj.anno_simple and
                self.anno_bound == obj.anno_bound and
                self.dipl_bound == obj.dipl_bound and
                self.line_break == obj.line_break
            )


class TextChar(Char):
    """Entspricht ehemaliges 'w' """
    pass

class Majuscule(TextChar):
    def __init__(self, _trans, size, dipl_utf="", anno_utf="", anno_simple=""):

        super(Majuscule, self).__init__(_trans, dipl_utf, anno_utf, anno_simple)
        self.size = size

class Whitespace:
    def __init__(self, _trans):
        self.string = _trans
        self.dipl_utf = _trans
        self.anno_utf = _trans
        self.anno_simple = _trans
        self.anno_bound = False
        self.dipl_bound = False
        self.line_break = False

class Joiner:
    pass


class Hyphen(TextChar, Joiner):
    """ehemalig 'dd' """
    pass

class Punct(Char):
    """ehemalig 'p' """
    pass

class MetaChar(Char):
    """ehemalig ptk, editnum, ill, br, maj, etc. """
    pass

class Bracket(MetaChar):
    def __init__(self, _trans, opening=True, **kwargs):
        self.opening = True
        super().__init__(_trans, **kwargs)

class Illegible(Bracket):
    pass

class Strikethrough(Bracket):
    pass

class SentBound(MetaChar):
    """ehemalig 'pe' """
    pass

class TokenBound(MetaChar):
    """ehemalig 'spl' """
    pass

class EditHyphen(TokenBound, Joiner):
    pass


#  actually both textchar (since "=" present in handschrift)
#     and meta (since "|" added by editor/transcriber)
class DiplJoiner(TokenBound, Joiner):
    """ oft =| """
    pass