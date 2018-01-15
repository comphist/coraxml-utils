

import anytree
from typing import List


BR = {'[': ']', ']': '[', 
      '(': ')', ')': '(',
      '{': '}', '}': '{',
      '<': '>', '>': '<'}


__version__ = "2018.01.12"


class BaseTrans:

    def __init__(self, myparse):
        self.parse = myparse


    def __len__(self):
        return len(self.parse)


    def __eq__(self, other):
        return self.parse == other.parse


    def __repr__(self):
        return str(self.parse)


    def __str__(self):
        return self.to_string()


    def __iadd__(self, other):
        return self.__class__(self.parse + other.parse)

       self.dipl_utf_opts = {"illegible": "character",
                            "strikethru": "leave",
                            "doubledash": True,
                            "preedpunc": False,
                            "preedtoken": False}
    def to_string(self, illegible="original", strikethru="original", doubledash=True,
                  preedpunc=True, preedtoken=True):
            
        for c in self.parse:

        return "".join(c.get("trans") for c in self.parse)


    def keep(self, *types):
        return self.__class__([c for c in self.parse if c["type"] in types])


    def has(self, *types):
        return any(c["type"] in types for c in self.parse)
        

    def delete(self, *types):
        return self.__class__([c for c in self.parse if c["type"] not in types])


    def flip_bracket(self, br_str):
        return "".join(BR.get(c, c) for c in br_str)



class AnnoTrans(BaseTrans):

    def __init__(self, myparse):
        super().__init__(myparse)

    def utf(self):
        return "".join(c.get("utf") for c in self.parse)

    def simple(self):
        return "".join(c.get("simple") for c in self.parse)


class DiplTrans(BaseTrans):

    def __init__(self, myparse):
        super().__init__(myparse)

    def utf(self):
        return "".join(c.get("utf") for c in self.parse)

    def get_subtoken_tree(self):
        # TODO
        pass


class Trans(BaseTrans):


    def __init__(self, myparse, anno_splits=None, dipl_splits=None, **kwargs):
        super().__init__(myparse)
        self.parse = myparse
        self.dipl_tok_bounds = dipl_splits if dipl_splits else []
        self.anno_tok_bounds = anno_splits if anno_splits else []

        for key, val in kwargs.items():
            setattr(self, key, val)


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




        # br_actions = self.set_illegible_options(illegible, character)

        # last_char = dict()
        # outstr = list()
        # last_index = len(self.parse) - 1

        # for i, c in enumerate(self.parse):
        #     before = ""
        #     after = ""
        #     skip_char = False

        #     # character conversion
        #     if character != "original":
        #         out_char = c[character]
        #     else:
        #         out_char = c["trans"]

        #     if not doubledash and c["type"] == "dd":
        #         skip_char = True

        #     if not editnum and c["type"] == "edit":
        #         skip_char = True

        #     brtype = c.get("brtype", None)
        #     # strikethru
        #     if brtype == "strk":
        #         if strikethru == "original":
        #             before = c.get("before", "")
        #             after = c.get("after", "")
        #         elif strikethru == "delete":
        #             skip_char = True

        #     # illegible character handling        
        #     elif brtype == "ill":
        #         if c["br"] in br_actions["original"]:
        #             before = c.get("before", "")
        #             after = c.get("after", "")
        #         # if last char is bracket end
        #         elif c.get("br") in br_actions["delete"] and i == last_index:
        #             before = self.illegible_replacement
        #             skip_char = True
        #         elif c.get("br") in br_actions["delete"]:
        #             # wait for bracket end, then add replacement (see below)
        #             skip_char = True
        #         else:
        #             if last_char.get("br") in br_actions["delete"]:
        #                 before = self.illegible_replacement
        #     else:
        #         if last_char.get("br") in br_actions["delete"]:
        #             before = self.illegible_replacement

        #     # pre-edition char handling
        #     if not preedpunc:
        #         if c["type"] in {"pe", "q"}:
        #             skip_char = True

        #     if not preedtoken:
        #         if (c["trans"] == "*f" or
        #             c["type"] == "ptk" or
        #             c["type"] == "spl"):
        #             skip_char = True

        #     outstr.append(before)
        #     if not skip_char:
        #         outstr.append(out_char)
        #     outstr.append(after)

        #     last_char = c

        # return "".join(outstr)


    def tokenize_anno(self) -> List[AnnoTrans]:
        output_tokens = list()
        stack = list()
        for i, c in enumerate(self.parse):
            if i + 1 in self.anno_tok_bounds:
                output_tokens.append(AnnoTrans(stack))
                stack = list()
            stack.append(c)
        output_tokens.append(AnnoTrans(stack))
        return output_tokens


    def tokenize_dipl(self) -> List[DiplTrans]:
        output_tokens = list()
        stack = list()
        for i, c in enumerate(self.parse):
            if i + 1 in self.dipl_tok_bounds:
                output_tokens.append(DiplTrans(stack))
                stack = list()
            stack.append(c)
        output_tokens.append(DiplTrans(stack))
        return output_tokens