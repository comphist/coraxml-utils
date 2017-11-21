 
# von transkription

 def __init__(self, intext):
        self.pages = list()
        self.columns = list()
        self.lines = list()
        self.tokens = list()
        self.shifttags = list()

        self.text = list()

        # read header
        header_open = False
        header_lines = list()

        for line in intext.splitlines():
            if line.strip() == "+H":
                header_open = True
            elif line.strip() == "@H":
                header_open = False
            elif header_open:
                header_lines.append(line)
            elif line and not header_open:
                self.text.append(line)
            else:
                # skip empty lines
                pass

        if not header_lines:
            raise Exception("ERROR: Header is empty!")

        self.headertext = "\n".join(header_lines)
        self.sigle = re.search(r"[^:\s]:\s+([\w\d]+)", self.headertext).group(1)

        this_line = None
        this_col = None
        this_page = None
        last_page = None
        last_side = None
        last_col = None
        last_line = None        
        in_comment = False
        open_shifttags = list()
        comment_stack = list()
        shifttag_stack = list()
        join_next_mods = False
        join_next_dipls = False
        for line in self.text:

            bibinfo, content, *_ = line.strip().split("\t")
            if _: print("WARNING   extraneous tab in line:", line)
            for match in BIBINFO_FORMAT.findall(bibinfo):
                sigle, pageno, side, col, linename = match
                this_line = Line(linename, loc=match[1:])

                if side != last_side or pageno != last_page:
                   # new page and col
                   this_col = Column(col)
                   this_col.lines.append(this_line)
                   this_page = Page(pageno, side)
                   this_page.columns.append(this_col)

                   self.pages.append(this_page)
                   self.columns.append(this_col)
                   self.lines.append(this_line)
                elif col != last_col:
                    # start new col
                    # (columns started this way have names)
                    this_col = Column(col)
                    this_col.lines.append(this_line)
                    this_page.columns.append(this_col)

                    self.columns.append(this_col)
                    self.lines.append(this_line)
                else:
                    self.lines.append(this_line)
                    this_col.lines.append(this_line)

                last_page = pageno
                last_side = side
                last_col = col

            for tok in content.split():
                # shifttags
                if re.match(r"\+[FLRÜMQ]p?", tok):
                    open_shifttags.append(tok[1:])
                elif re.match(r"@([FLRÜMQ]p?)", tok):
                    closed_shifttag = open_shifttags.pop()
                    self.shifttags.append(ShiftTag(closed_shifttag, shifttag_stack))
                    if not open_shifttags:
                        shifttag_stack = list()

                # comments
                elif re.match(r"\+[KEZ]", tok):
                  in_comment = True
                elif re.match(r"@([KEZ])", tok):
                  in_comment = False
                  self.tokens.append(Comment(tok[1], comment_stack))
                  comment_stack = list()

                # tokens
                else:
                    if in_comment:
                        comment_stack.append(tok)
                    else:
                        new_token = Token(tok)
                        mtok = ParsedToken(tok, Options())

                        if not mtok.parse:
                            raise Exception("token has empty parse: " + tok)

                        # put edition numbering in comments
                        if mtok.parse[0]["type"] == "edit":
                            self.tokens.append(Comment("Z", [tok]))
                            continue

                        dtrans = str(mtok.with_opts(DIPL_TRANS_OPTS).tokenize()).split()
                        dutfs = str(mtok.with_opts(DIPL_UTF_OPTS).tokenize()).split()
                        mtrans = str(mtok.with_opts(MOD_TRANS_OPTS).tokenize()).split()
                        mutfs = str(mtok.with_opts(MOD_UTF_OPTS).tokenize()).split()
                        msimple = str(mtok.with_opts(MOD_SIMPLE_OPTS).tokenize()).split()

                        if len(dtrans) != len(dutfs):
                            raise Exception("dipl length not equal")
                        if len(mtrans) != len(msimple):
                            if len(msimple) < len(mtrans):
                                while len(msimple) != len(mtrans):
                                    msimple.append("")
                            else:
                                raise Exception("mod length not equal")

                        for dt, du in zip(dtrans, dutfs):
                            new_token.dipls.append(Dipl(dt, du))

                        for mt, mu, ms in zip(mtrans, mutfs, msimple):
                            new_token.mods.append(Mod(mt, mu, ms))

                        for d in new_token.dipls:
                            this_line.tokens.append(d)

                        if join_next_mods or join_next_dipls:
                            i = -1
                            while i > -10:  # arbitrary limit on number of intervening comments
                                if isinstance(self.tokens[i], Comment):
                                    i -= 1
                                else:
                                    self.tokens[i].merge_token(new_token, join_next_dipls, join_next_mods)
                                    break
                            join_next_mods = False
                            join_next_dipls = False
                        else:
                            self.tokens.append(new_token)
                            if open_shifttags:
                                shifttag_stack.append(new_token)
                        
                        if mtok.parse:
                            join_next_mods = mtok.parse[-1]["char"] in {"(=)", "="}
                            join_next_dipls = mtok.parse[-1]["char"] in {"=|"}

            # at end of line
            last_line = this_line

        self.generate_IDs()
