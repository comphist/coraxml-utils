

BR = {'[': ']', ']': '[', 
      '(': ')', ')': '(',
      '{': '}', '}': '{',
      '<': '>', '>': '<'}


__version__ = "2017.12.05"


class ParsedToken:
    def __init__(self, intoken, illegible_replacement="[...]", missing_br_open="[",
                 dipl_utf_opts=None, anno_utf_opts=None, anno_simple_opts=None):
        self.parse = intoken
        self.illegible_replacement = illegible_replacement
        self.missing_br_open = missing_br_open

        self.options = dict()
        self.options["dipl_utf"] = dipl_utf_opts if dipl_utf_opts else dict()
        self.options["anno_utf"] = anno_utf_opts if anno_utf_opts else dict()
        self.options["anno_simple"] = anno_simple_opts if anno_simple_opts else dict()


    def __len__(self):
        return len(self.parse)


    def __eq__(self, other):
        return self.parse == other.parse


    def __repr__(self):
        return str(self.parse)


    def __str__(self):
        return self.to_string(illegible="original", 
                              character="original",
                              doubledash=True,
                              editnum=True,
                              strikethru="original",
                              preedpunc=True,
                              preedtoken=True)


    def __iadd__(self, other):
        return self.__class__(self.parse + other.parse)


    def set_illegible_options(self, opt_ill, opt_char):
        # setting illegible options:
        #   lists contain bracket types for which each
        #   action (one list per action) is to be carried out

        br_actions = {"leave": list(),
                      "delete": list(),
                      "original": list()}

        if opt_ill == "delete":
            br_actions["delete"] = ["<", "<<", "[", "[["]
        elif opt_ill == "leave":
            br_actions["leave"] = ["<", "<<", "[", "[["]
        elif opt_ill == "original":
            br_actions["original"] = ["<", "<<", "[", "[["]
        elif opt_ill == "character":
            if opt_char == "utf":
                br_actions["delete"] = ["[", "[["]
                br_actions["leave"] = ["<", "<<"]
            elif opt_char == "simple":
                br_actions["leave"] = ["<", "["]
                br_actions["original"] = ["[[", "<<"]
            else:
                # the character/orig combo should lead here
                br_actions["original"] = ["<", "<<",  "[", "[["]
        else:
            br_actions["leave"] = ["<", "<<", "[", "[["]  
        return br_actions        


    def to_string(self, 
                  illegible="leave", 
                  character="utf",
                  doubledash=False,
                  editnum=False,
                  strikethru="leave",
                  preedpunc=True,
                  preedtoken=False):
        br_actions = self.set_illegible_options(illegible, character)

        last_char = dict()
        outstr = list()
        last_index = len(self.parse) - 1

        for i, c in enumerate(self.parse):
            before = ""
            after = ""
            skip_char = False

            # character conversion
            if character != "original":
                out_char = c[character]
            else:
                out_char = c["trans"]

            if not doubledash and c["type"] == "dd":
                skip_char = True

            if not editnum and c["type"] == "edit":
                skip_char = True

            brtype = c.get("brtype", None)
            # strikethru
            if brtype == "strk":
                if strikethru == "original":
                    before = c.get("before", "")
                    after = c.get("after", "")
                elif strikethru == "delete":
                    skip_char = True

            # illegible character handling        
            elif brtype == "ill":
                if c["br"] in br_actions["original"]:
                    before = c.get("before", "")
                    after = c.get("after", "")
                # if last char is bracket end
                elif c.get("br") in br_actions["delete"] and i == last_index:
                    before = self.illegible_replacement
                    skip_char = True
                elif c.get("br") in br_actions["delete"]:
                    # wait for bracket end, then add replacement (see below)
                    skip_char = True
                else:
                    if last_char.get("br") in br_actions["delete"]:
                        before = self.illegible_replacement
            else:
                if last_char.get("br") in br_actions["delete"]:
                    before = self.illegible_replacement

            # pre-edition char handling
            if not preedpunc:
                if c["type"] in {"pe", "q"}:
                    skip_char = True

            if not preedtoken:
                if (c["trans"] == "*f" or
                    c["type"] == "ptk" or
                    c["type"] == "spl"):
                    skip_char = True

            outstr.append(before)
            if not skip_char:
                outstr.append(out_char)
            outstr.append(after)

            last_char = c

        return "".join(outstr)


    def keep(self, *types):
        return self.__class__([c for c in self.parse if c["type"] in types])


    def has(self, *types):
        return any(c["type"] in types for c in self.parse)
        

    def delete(self, *types):
        return self.__class__([c for c in self.parse if c["type"] not in types])


    def flip_bracket(self, br_str):
        return "".join(BR.get(c, c) for c in br_str)


    def tokenize(self, tokenize_type="all", split_init_punc=True):
        new_parse = list()
        padded_parse = ([{"trans": "", "type": "spc"}] + 
                        self.parse + 
                        [{"trans": "", "type": "spc"}])

        for i in range(1, len(padded_parse) - 1):
            last_char, this_char, next_char = padded_parse[i-1:i+2]

            my_bracket = this_char.get("br", None)
            conditions = []
            postspace_conds = []

            if (tokenize_type == "medium" or 
                tokenize_type == "all"):
                # word split "foo|bar"
                conditions.append(last_char["type"] == "spl" and 
                                  last_char["trans"].endswith("|"))

                if tokenize_type == "all":
                    if split_init_punc:
                        # initial punctuation "//foo"
                        conditions.append(last_char["type"] in {"ip", "q"})

                    # other initial punctuation
                    postspace_conds.append(last_char["type"] in {"spc", None} and
                                           this_char["type"] == "p" and
                                           this_char["trans"] != "." and 
                                           next_char["type"] == "w")

                    # final punctuation  "foo%." (NOT "f%.oo")
                    conditions.append(last_char["type"] not in {"br", "spc", "spl"} and
                                      this_char["type"] in {"ip", "p", "pe", "q"} and 
                                      this_char["trans"] != '.' and
                                      next_char["type"] != "w" and
                                      next_char["trans"] not in {'(=)', '#'})

                    # rule for periods (which can be periods or unreadable chars)
                    conditions.append(last_char["type"] not in {"spc", "spl"} and
                                      this_char["trans"] == "." and 
                                      next_char["type"] != "w" and 
                                      next_char["trans"] not in {'(=)', '#'} and
                                       # tokenize when period not in missing char parens
                                      (my_bracket not in self.missing_br_open or
                                       # tokenize when period is alone in parens
                                       (this_char.get("before") and 
                                        this_char.get("after") and
                                        this_char.get("brtype") == "ill")))

                    # ptk marker after punctuation  "foo.*2"
                    conditions.append(this_char["type"] == "ptk" and 
                                      last_char["type"] in {"ip", "p", "pe", "q"})

            elif tokenize_type == "historical":
                conditions.append(last_char["type"] == "spl" and 
                                  last_char["trans"].endswith('#'))

            else:
                # do nothing -- no tokenization
                pass

            this_char_copy = this_char.copy()  # prevents tokenization side-effects
            if any(conditions):
                if my_bracket:
                    if new_parse:
                        # close bracket before space
                        new_parse[-1]["after"] = self.flip_bracket(my_bracket)
                        
                        print("kommt vor!", str(self))

                    # reopen after space
                    this_char_copy["before"] = my_bracket

                new_parse.append({"trans": " ", "type": "spc"})
                new_parse.append(this_char_copy)

            elif any(postspace_conds):
                new_parse.append(this_char_copy)
                new_parse.append({"trans": " ", "type": "spc"})
            else:
                new_parse.append(this_char_copy)

        new_tokens = list()
        stack = list()
        for c in new_parse:
            if c["type"] == "spc":
                if stack:
                    new_tokens.append(self.__class__(stack,
                                                     illegible_replacement=self.illegible_replacement,
                                                     missing_br_open=self.missing_br_open,
                                                     dipl_utf_opts=self.options["dipl_utf"], 
                                                     anno_utf_opts=self.options["anno_utf"],
                                                     anno_simple_opts=self.options["anno_simple"]))
                    stack = list()
            else:
                stack.append(c)
        new_tokens.append(self.__class__(stack,
                                         illegible_replacement=self.illegible_replacement,
                                         missing_br_open=self.missing_br_open,
                                         dipl_utf_opts=self.options["dipl_utf"], 
                                         anno_utf_opts=self.options["anno_utf"],
                                         anno_simple_opts=self.options["anno_simple"]))        
        return new_tokens


    def tokenize_dipl(self):
        return self.tokenize(tokenize_type="historical")


    def tokenize_anno(self):
        return self.tokenize(tokenize_type="all", split_init_punc=False)


    def dipl_utf(self):
        return self.to_string(**self.options["dipl_utf"])


    def anno_utf(self):
        return self.to_string(**self.options["anno_utf"])


    def anno_simple(self):
        return self.to_string(**self.options["anno_simple"])
