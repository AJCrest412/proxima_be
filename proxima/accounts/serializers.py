from rest_framework import serializers
from .models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        try:
            data = super().validate(attrs)
        except AuthenticationFailed as e:
            raise AuthenticationFailed({'success': False, 'message': 'Invalid email or password'})

        # Add user information
        data.update({
            'data' : { 'user_id': self.user.id,
                       'email': self.user.email,
                       'name': self.user.name}
                       ,
            'success': True,
            'message': 'Login successful'
        }) # type: ignore

        return data

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'name']
        
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['email', 'name', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            name=validated_data.get('name', ''),
            password=validated_data['password']
        )
        return user