import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

const String kApiBase = 'https://api.neurotwin.ai';

class AuthService {
  AuthService._();
  static final instance = AuthService._();
  final _storage = const FlutterSecureStorage();

  Future<String?> getAccessToken() => _storage.read(key: 'access_token');

  Future<bool> login(String email, String password) async {
    final resp = await http.post(
      Uri.parse('$kApiBase/v1/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );
    if (resp.statusCode == 200) {
      final data = jsonDecode(resp.body);
      await _storage.write(key: 'access_token', value: data['access_token']);
      await _storage.write(key: 'refresh_token', value: data['refresh_token']);
      return true;
    }
    return false;
  }

  Future<bool> register(String name, String email, String password) async {
    final resp = await http.post(
      Uri.parse('$kApiBase/v1/auth/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'name': name, 'email': email, 'password': password}),
    );
    if (resp.statusCode == 201) {
      final data = jsonDecode(resp.body);
      await _storage.write(key: 'access_token', value: data['access_token']);
      await _storage.write(key: 'refresh_token', value: data['refresh_token']);
      return true;
    }
    return false;
  }

  Future<void> logout() async {
    await _storage.deleteAll();
  }
}
