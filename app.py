from flask import Flask, render_template, Response, jsonify
from deepface import DeepFace  # type: ignore
import cv2
from spotify_integration import authenticate_spotify, get_playlist_for_mood

app = Flask(__name__)
camera = cv2.VideoCapture(0)

sp = authenticate_spotify()  # Initialize Spotify API client
detected_emotion = None  # Variable to store the current detected emotion

def gen_frames():
    global detected_emotion
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            try:
                # Analyze the frame for emotions
                results = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
                result = results[0] if isinstance(results, list) else results
                
                if result and 'dominant_emotion' in result:
                    detected_emotion = result['dominant_emotion']
                else:
                    detected_emotion = "No face detected"

                # Display emotion on the video feed
                cv2.putText(frame, f"Emotion: {detected_emotion}", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            except Exception as e:
                detected_emotion = "No face detected"
                print(f"Error: {e}")

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/recommend-music', methods=['GET'])
def recommend_music():
    global detected_emotion
    print(f"Detected Emotion: {detected_emotion}")  # Log the detected emotion
    
    if detected_emotion == "No face detected":
        return jsonify({"emotion": "No face detected", "message": "Please ensure your face is visible to the camera."})
    elif detected_emotion:
        playlist_uri = get_playlist_for_mood(detected_emotion, sp)
        if playlist_uri:
            print(f"Returning playlist URI: {playlist_uri}")
            return jsonify({"emotion": detected_emotion, "playlist_uri": playlist_uri})
        else:
            return jsonify({"error": "No playlist found for the detected emotion"}), 404
    else:
        return jsonify({"error": "No emotion detected yet"}), 400

if __name__ == '__main__':
    app.run(debug=True)
