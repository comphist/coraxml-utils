



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

