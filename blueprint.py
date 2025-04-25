""" AMI Core Headspace Blueprint for Calendar """

from flask import request, jsonify

from ami.headspace.blueprint import Blueprint, HeaderButton, route, render_template
from .google_sync import GoogleAuth

class Calendar(Blueprint):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_tempsets(css='sync.css')

        self.auth = GoogleAuth(self.filesystem.path)

    @route('/sync_google')
    def sync_google(self):
        """Landing page with instructions for users"""
        return render_template(
            'sync_google.html',
            tempsets=self.tempsets.augment(
                header="Set Up Google Calendar Access"
            )
        )

    @route('/auth_status')
    def auth_status(self):
        """Check if user is currently authorized"""
        try:
            return jsonify({'authorized': self.auth.is_valid()})

        except Exception as e:
            return jsonify({
                'authorized': False,
                'error': str(e)
            })

    @route('/upload_google_credentials', methods=['POST'])
    def upload_google_credentials(self):
        try:
            if 'credentials' not in request.files:
                return jsonify({'success': False, 'message': 'No file part in the request'}), 400

            file = request.files['credentials']

            if file.filename == '':
                return jsonify({'error': 'No file selected for uploading'}), 400

            if file:
                self.auth.clear_creds_and_token()
                file.save(self.auth.credentials_save_path)
                return jsonify({'success': True, 'message': 'Credentials uploaded successfully'}), 200

        except Exception as e:
            self.logs.error(f"Error uploading credentials: {str(e)}")
            return jsonify({'error': f'Failed to upload credentials: {str(e)}'}), 500

    @route('/initiate_auth', methods=['GET','POST'])
    def initiate_auth(self):
        """Initiates the OAuth flow using the user's credentials"""
        try:
            creds = self.auth.get_credentials()

            if not creds:
                return jsonify({
                    'error': 'Client secret file not found',
                    'message': 'Please complete the setup instructions first'
                }), 404

            return jsonify({
                'success': True,
                'message': 'Authorization successful! You can now access your calendar.'
            })

        except Exception as e:
            return jsonify({
                'error': str(e),
                'message': 'Authorization failed. Find another way to attempt this. Good luck.'
            }), 400
