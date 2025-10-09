# VigilantEye - AI-Powered Security & Surveillance System

![VigilantEye Logo](https://img.shields.io/badge/VigilantEye-AI%20Security-blue?style=for-the-badge&logo=eye)

A comprehensive AI-powered security and surveillance system with integrated face detection, recognition, and demographics analysis capabilities.

## 🚀 Features

### Core Security Features
- **User Authentication & Management** - Secure login/registration system
- **Session Management** - Robust session handling with security controls
- **Real-time Monitoring** - Live surveillance capabilities
- **Data Analytics** - Comprehensive analytics dashboard

### AI-Powered Features
- **Face Detection & Recognition** - Advanced face detection using OpenCV
- **Demographics Analysis** - Age and gender estimation
- **Real-time Processing** - Live image analysis and processing
- **Smart Alerts** - Intelligent notification system
- **Analytics Dashboard** - Comprehensive AI insights and statistics

### Technical Features
- **Responsive Web Interface** - Modern, mobile-friendly design
- **RESTful API** - Well-structured API endpoints
- **Database Integration** - MySQL/SQLite database support
- **Deployment Ready** - Vercel, Heroku, and Docker support
- **Graceful Degradation** - Works with or without full AI dependencies

## 🛠️ Technology Stack

### Backend
- **Python 3.8+** - Core programming language
- **Flask** - Web framework
- **OpenCV** - Computer vision library
- **Face Recognition** - Face detection and recognition
- **NumPy** - Numerical computing
- **Pillow** - Image processing
- **scikit-learn** - Machine learning utilities

### Frontend
- **HTML5/CSS3** - Modern web standards
- **Bootstrap 5** - Responsive UI framework
- **JavaScript** - Interactive functionality
- **Bootstrap Icons** - Professional iconography

### Database
- **SQLite** - Default database (development)
- **MySQL** - Production database support

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Git

### Quick Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/VigilantEye.git
   cd VigilantEye
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Face AI dependencies (Optional)**
   ```bash
   # For full AI functionality
   ./install_face_ai.bat  # Windows
   # or
   pip install opencv-python face-recognition Pillow scikit-learn matplotlib numpy
   ```

4. **Run the application**
   ```bash
   python vigilanteye_integrated.py
   ```

5. **Access the application**
   - Main Dashboard: `http://localhost:8080`
   - Face AI Dashboard: `http://localhost:8080/face-ai`
   - Features Page: `http://localhost:8080/features`

## 🎯 Usage

### Basic Usage
1. **Register/Login** - Create an account or login
2. **Dashboard** - View system overview and statistics
3. **Face AI** - Upload images for face detection and analysis
4. **Features** - Explore all available features

### Face AI Analysis
1. Navigate to the Face AI dashboard
2. Upload an image (drag & drop or click to select)
3. Choose analysis type:
   - **Full Analysis** - Complete face detection with demographics
   - **Quick Scan** - Basic face detection only
4. View results and statistics

### API Endpoints

#### Authentication
- `POST /login` - User login
- `POST /signup` - User registration
- `GET /logout` - User logout

#### Face AI
- `POST /face-ai/detect` - Full face analysis with demographics
- `POST /face-ai/detect-simple` - Basic face detection
- `GET /face-ai/stats` - Get analysis statistics
- `POST /face-ai/reset` - Reset statistics

## 🚀 Deployment

### Vercel Deployment
1. Connect your GitHub repository to Vercel
2. Configure environment variables if needed
3. Deploy automatically on push

### Heroku Deployment
1. Install Heroku CLI
2. Create Heroku app
3. Deploy using Git

### Docker Deployment
1. Build Docker image
2. Run container with appropriate ports

## 📁 Project Structure

```
VigilantEye/
├── face_ai/                    # Face AI modules
│   ├── models/                 # AI model files
│   ├── uploads/                # Image upload directory
│   ├── FaceDetection.py        # Face detection logic
│   ├── demographics.py         # Demographics analysis
│   └── face_detection_api.py   # Face AI API
├── templates/                  # HTML templates
│   ├── base.html              # Base template
│   ├── dashboard.html         # Main dashboard
│   ├── features.html          # Features page
│   └── face_ai_unavailable.html
├── static/                     # Static assets
│   ├── style.css              # Main stylesheet
│   └── script.js              # JavaScript functionality
├── vigilanteye_integrated.py   # Main application
├── requirements.txt            # Python dependencies
├── install_face_ai.bat        # Face AI installation script
└── README.md                  # This file
```

## 🔧 Configuration

### Environment Variables
- `FLASK_ENV` - Flask environment (development/production)
- `DATABASE_URL` - Database connection string
- `SECRET_KEY` - Flask secret key for sessions

### Face AI Configuration
- Model files are automatically downloaded on first run
- Upload directory is created automatically
- Statistics are stored in memory (can be configured for database storage)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Sameer Pyarali Keshvani**
- GitHub: [@sameerkeshvani](https://github.com/sameerkeshvani)
- Project Link: [https://github.com/sameerkeshvani/VigilantEye](https://github.com/sameerkeshvani/VigilantEye)

## 🙏 Acknowledgments

- OpenCV community for computer vision tools
- Face Recognition library contributors
- Bootstrap team for the UI framework
- Flask community for the web framework

## 📊 Project Status

![GitHub last commit](https://img.shields.io/github/last-commit/sameerkeshvani/VigilantEye)
![GitHub issues](https://img.shields.io/github/issues/sameerkeshvani/VigilantEye)
![GitHub pull requests](https://img.shields.io/github/issues-pr/sameerkeshvani/VigilantEye)
![GitHub stars](https://img.shields.io/github/stars/sameerkeshvani/VigilantEye)

---

**VigilantEye** - *Your AI-Powered Security Solution* 🛡️👁️