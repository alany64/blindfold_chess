from candidate_moves import *

TAKE_TOKENS = {'takes', 'captures'}
PROMOTE_TOKENS = {'promote', 'equals'}
KINGSIDE_TOKENS = {'king', 'short'}
QUEENSIDE_TOKENS = {'queen', 'long'}

WRITTEN_NUMS = {'one': '1', 'two': '2', 'three': '3', 'four': '4',
                'five': '5', 'six': '6', 'seven': '7', 'eight': '8'}


def locations_in_tokens(tokens: List[str], turn: bool) -> List[SpecificSquares]:
    """
    Parse tokens by constructing a SpecificSquares for each group of adjacent
    words that could correspond to one.

    :param tokens: the words in the spoken request
    :param turn: whose turn it is - True if white, False if Black
    :return: a list of SpecificSquares in the same order they were extracted
    from the request
    """
    if not tokens:
        return []

    loc = SpecificSquares(turn)
    locations = []
    for i, token in enumerate(tokens):
        if token in PIECES and not loc:
            loc.piece = token
        elif token == 'on':
            continue
        elif token in FILES and not loc.file and not loc.rank:
            loc.file = token
        elif token in WRITTEN_NUMS and not loc.rank:
            loc.rank = WRITTEN_NUMS[token]
        else:
            if not (token in PIECES or token in FILES or token in RANKS):
                i += 1
            locations.extend(locations_in_tokens(tokens[i:], not turn))
            break

    if loc:
        locations.insert(0, loc)
    return locations


def decipher_request(request: str, board: chess.Board):
    """
    Determine the intent of request and parse it for the information needed to
    address it.

    :param request: a spoken request pertaining to the current game
    :param board: the board state representing the current game
    """
    if request == 'why':
        return request

    tokens = request.split()
    token_set = set(tokens)

    if 'castle' in tokens:
        if token_set & KINGSIDE_TOKENS:
            castle_command = CastleCommand(board, 'king')
        elif token_set & QUEENSIDE_TOKENS:
            castle_command = CastleCommand(board, 'queen')
        else:
            castle_command = CastleCommand(board)
        castle_command.consider_moves()
        return castle_command

    does_take = bool(token_set & TAKE_TOKENS)
    does_promote = token_set & PROMOTE_TOKENS
    say_promotes = tokens[-1] if does_promote else None
    if does_promote:
        # do not want to construct a SpecificSquares solely for promotion piece
        locations = locations_in_tokens(tokens[:-1], board.turn)
    else:
        locations = locations_in_tokens(tokens, board.turn)

    if len(locations) == 1:
        if locations[0].file and locations[0].rank:
            # command spoken in standard algebraic notation
            # move like Na3 must be broken up,
            # represents both start and end destination
            to_where = locations[0]
            if to_where.piece:
                from_piece = to_where.piece
            else:
                from_piece = 'pawn'
            from_where = SpecificSquares(board.turn, from_piece)
            to_where.color = not board.turn
            to_where.piece = None
            command_move = CommandMove(
                board, from_where, to_where, does_take, say_promotes)
        elif does_take:
            # intent is to take last piece moved by opponent
            command_move = take_last(locations[0], board, say_promotes)
        else:
            # should only be 2 cases, potential to add more in future
            assert False
    else:
        command_move = CommandMove(
            board, locations[0], locations[1], does_take, say_promotes)
    command_move.consider_moves()
    return command_move
