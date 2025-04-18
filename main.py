import socket
import threading
import pygame
import sys
import chess
import random

# Initialize pygame
pygame.init()

# Game constants
board_size = 8
square_size = 110
WIDTH = square_size * board_size + 250
HEIGHT = square_size * board_size

# Colors
white = (255, 255, 255)
black = (0, 0, 0)
light_square_color = (254, 254, 220)
dark_square_color = (125, 135, 150)
blue = (0, 0, 255)

# Font for text
font = pygame.font.Font(None, 36)
small_font = pygame.font.Font(None, 24)

# Create a pygame window
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chess Game with LAN & AI")

# Initialize the chessboard
board = chess.Board()

# Networking variables
sock = None
is_server = None
turn = True
move_list = []
viewer_sockets = []

# AI-related variables
play_with_ai = False
ai_depth = 2
player_color = chess.WHITE

# Function to initialize the network or AI
def setup_connection():
    global sock, is_server, turn, play_with_ai, ai_depth, player_color
    print("Select game mode:")
    print("1. LAN - Server")
    print("2. LAN - Client")
    print("3. Viewer")
    print("4. Play against AI")
    role = input("Enter choice (1-4): ").strip()

    if role == "1":
        is_server = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("0.0.0.0", 5555))
        sock.listen(5)
        print("Waiting for connections...")
        threading.Thread(target=handle_connections, daemon=True).start()
    elif role == "2":
        is_server = False
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_ip = input("Enter the server IP address: ").strip()
        sock.connect((server_ip, 5555))
        print("Connected to the server.")
        turn = False
    elif role == "3":
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_ip = input("Enter the server IP address: ").strip()
        sock.connect((server_ip, 5555))
        print("Connected as a viewer.")
        threading.Thread(target=receive_updates, daemon=True).start()
        while True:
            pass
    elif role == "4":
        play_with_ai = True
        color = input("Do you want to play as White or Black? (w/b): ").strip().lower()
        player_color = chess.WHITE if color == 'w' else chess.BLACK
        turn = player_color == chess.WHITE
        ai_depth = int(input("Select AI difficulty (1-4): ").strip())
        print(f"You are playing as {'White' if player_color == chess.WHITE else 'Black'}.")
    else:
        print("Invalid role. Restart and choose again.")
        sys.exit()

def handle_connections():
    global viewer_sockets
    while True:
        conn, addr = sock.accept()
        role = conn.recv(1024).decode()
        if role == "viewer":
            viewer_sockets.append(conn)
            print(f"Viewer connected from {addr}")
        else:
            print(f"Player connected from {addr}")
            threading.Thread(target=receive_moves, args=(conn,), daemon=True).start()

def send_move(move):
    if sock:
        sock.send(move.encode())
    for viewer in viewer_sockets:
        try:
            viewer.send(move.encode())
        except:
            viewer_sockets.remove(viewer)

def receive_moves(conn):
    global turn
    while True:
        try:
            move = conn.recv(1024).decode()
            if move:
                print(f"Move received: {move}")
                board.push_uci(move)
                move_list.append(move)
                turn = not turn
                broadcast_to_viewers(move)
        except Exception as e:
            print(f"Error receiving move: {e}")
            break

def broadcast_to_viewers(move):
    for viewer in viewer_sockets:
        try:
            viewer.send(move.encode())
        except:
            viewer_sockets.remove(viewer)

def receive_updates():
    while True:
        try:
            move = sock.recv(1024).decode()
            if move:
                print(f"Game update: {move}")
                board.push_uci(move)
        except Exception as e:
            print(f"Error receiving update: {e}")
            break

def draw_board(highlight_squares=[]):
    for row in range(board_size):
        for col in range(board_size):
            color = light_square_color if (row + col) % 2 == 0 else dark_square_color
            rect = pygame.Rect(col * square_size, row * square_size, square_size, square_size)
            pygame.draw.rect(screen, color, rect)
            if (row, col) in highlight_squares:
                pygame.draw.rect(screen, blue, rect, 4)

def draw_pieces():
    piece_images = {
        'P': pygame.image.load('images/white_pawn.png'),
        'R': pygame.image.load('images/white_rook.png'),
        'N': pygame.image.load('images/white_knight.png'),
        'B': pygame.image.load('images/white_bishop.png'),
        'K': pygame.image.load('images/white_king.png'),
        'Q': pygame.image.load('images/white_queen.png'),

        'p': pygame.image.load('images/black_pawn.png'),
        'r': pygame.image.load('images/black_rook.png'),
        'n': pygame.image.load('images/black_knight.png'),
        'b': pygame.image.load('images/black_bishop.png'),
        'k': pygame.image.load('images/black_king.png'),
        'q': pygame.image.load('images/black_queen.png'),
    }

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            row, col = divmod(square, 8)
            piece_image = piece_images.get(piece.symbol())
            if piece_image:
                piece_image = pygame.transform.scale(piece_image, (square_size, square_size))
                screen.blit(piece_image, (col * square_size, (7 - row) * square_size))

def draw_move_list():
    y_offset = 20
    for i, move in enumerate(move_list):
        move_text = small_font.render(move, True, white)
        screen.blit(move_text, (square_size * 8 + 10, y_offset))
        y_offset += 25

def handle_move(from_square, to_square):
    global turn
    move_uci = from_square + to_square
    move = chess.Move.from_uci(move_uci)
    if move in board.legal_moves:
        board.push(move)
        move_list.append(move_uci)
        if not play_with_ai:
            send_move(move_uci)
        turn = not turn

def ai_move():
    move = minimax_root(ai_depth, board, board.turn == chess.WHITE, -float('inf'), float('inf'))
    if move:
        board.push(move)
        move_list.append(move.uci())
        return True
    return False

def minimax_root(depth, board, is_maximizing, alpha, beta):
    best_move = None
    best_value = -float('inf') if is_maximizing else float('inf')
    for move in board.legal_moves:
        board.push(move)
        value = minimax(depth - 1, board, not is_maximizing, alpha, beta)
        board.pop()
        if is_maximizing and value > best_value:
            best_value = value
            best_move = move
        elif not is_maximizing and value < best_value:
            best_value = value
            best_move = move
    return best_move

def minimax(depth, board, is_maximizing, alpha, beta):
    if depth == 0 or board.is_game_over():
        return evaluate_board(board)

    if is_maximizing:
        max_eval = -float('inf')
        for move in board.legal_moves:
            board.push(move)
            eval = minimax(depth - 1, board, False, alpha, beta)
            board.pop()
            max_eval = max(max_eval, eval)
            alpha = max(alpha, eval)
            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = float('inf')
        for move in board.legal_moves:
            board.push(move)
            eval = minimax(depth - 1, board, True, alpha, beta)
            board.pop()
            min_eval = min(min_eval, eval)
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval

def evaluate_board(board):
    piece_values = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: 0
    }
    value = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            piece_value = piece_values[piece.piece_type]
            value += piece_value if piece.color == chess.WHITE else -piece_value
    return value

def main():
    global turn, start_square
    setup_connection()
    start_square = None
    highlighted_moves = []

    while True:
        if play_with_ai and board.turn != player_color:
            ai_move()
            turn = not turn

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and turn == player_color:
                x, y = pygame.mouse.get_pos()
                col, row = x // square_size, y // square_size
                row_board = 7 - row if player_color == chess.BLACK else row
                col_board = 7 - col if player_color == chess.BLACK else col
                square = chess.square(col_board, 7 - row_board)

                if start_square is None:
                    start_square = square
                    piece = board.piece_at(square)
                    if piece and piece.color == player_color:
                        highlighted_moves = [(7 - chess.square_rank(m.to_square), chess.square_file(m.to_square))
                                             for m in board.legal_moves if m.from_square == square]
                    else:
                        start_square = None
                        highlighted_moves = []
                else:
                    handle_move(chess.square_name(start_square), chess.square_name(square))
                    start_square = None
                    highlighted_moves = []

        screen.fill(black)
        draw_board(highlighted_moves)
        draw_pieces()
        draw_move_list()
        pygame.display.flip()

if __name__ == "__main__":
    main()