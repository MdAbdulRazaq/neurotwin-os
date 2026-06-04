import 'package:flutter/material.dart';
import '../services/auth_service.dart';
import 'chat_screen.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});
  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  bool _isLogin = true;
  bool _loading = false;
  bool _showPw = false;
  String _error = '';

  final _nameCtrl  = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _pwCtrl    = TextEditingController();

  Future<void> _submit() async {
    setState(() { _loading = true; _error = ''; });
    try {
      bool ok;
      if (_isLogin) {
        ok = await AuthService.instance.login(_emailCtrl.text.trim(), _pwCtrl.text);
      } else {
        ok = await AuthService.instance.register(
            _nameCtrl.text.trim(), _emailCtrl.text.trim(), _pwCtrl.text);
      }
      if (ok && mounted) {
        Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const ChatScreen()));
      } else {
        setState(() => _error = 'Authentication failed. Check your credentials.');
      }
    } catch (e) {
      setState(() => _error = 'Network error: $e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF060910),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(28),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 48),
              // Logo
              Row(
                children: [
                  Container(
                    width: 48, height: 48,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                        begin: Alignment.topLeft, end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: const Icon(Icons.auto_awesome, color: Colors.white, size: 22),
                  ),
                  const SizedBox(width: 14),
                  const Text('NEUROTWIN',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900,
                          color: Colors.white, letterSpacing: 2)),
                ],
              ),
              const SizedBox(height: 40),
              Text(
                _isLogin ? 'Welcome back' : 'Create your twin',
                style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w800,
                    color: Colors.white, letterSpacing: -0.5),
              ),
              const SizedBox(height: 8),
              Text(
                _isLogin
                    ? 'Your digital companion is waiting'
                    : 'Begin your journey with an AI that truly knows you',
                style: const TextStyle(fontSize: 14, color: Color(0xFF6B7280), height: 1.5),
              ),
              const SizedBox(height: 32),

              // Name field (register only)
              if (!_isLogin) ...[
                _label('Name'),
                const SizedBox(height: 6),
                _field(controller: _nameCtrl, hint: 'Your name', inputType: TextInputType.name),
                const SizedBox(height: 16),
              ],

              _label('Email'),
              const SizedBox(height: 6),
              _field(controller: _emailCtrl, hint: 'you@example.com', inputType: TextInputType.emailAddress),
              const SizedBox(height: 16),

              _label('Password'),
              const SizedBox(height: 6),
              _pwField(),
              const SizedBox(height: 20),

              if (_error.isNotEmpty)
                Container(
                  padding: const EdgeInsets.all(14),
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: const Color(0x1FEF4444),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0x40EF4444)),
                  ),
                  child: Text(_error,
                      style: const TextStyle(color: Color(0xFFF87171), fontSize: 13)),
                ),

              // Submit button
              GestureDetector(
                onTap: _loading ? null : _submit,
                child: Container(
                  height: 52,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                    ),
                    borderRadius: BorderRadius.circular(14),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFF6366F1).withOpacity(0.35),
                        blurRadius: 20, offset: const Offset(0, 6),
                      ),
                    ],
                  ),
                  child: Center(
                    child: _loading
                        ? const SizedBox(width: 22, height: 22,
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(_isLogin ? 'Sign in' : 'Get started',
                                  style: const TextStyle(color: Colors.white,
                                      fontSize: 16, fontWeight: FontWeight.w700)),
                              const SizedBox(width: 8),
                              const Icon(Icons.arrow_forward_rounded, color: Colors.white, size: 18),
                            ],
                          ),
                  ),
                ),
              ),

              const SizedBox(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    _isLogin ? "Don't have an account? " : "Already have an account? ",
                    style: const TextStyle(color: Color(0xFF6B7280), fontSize: 13),
                  ),
                  GestureDetector(
                    onTap: () => setState(() { _isLogin = !_isLogin; _error = ''; }),
                    child: Text(
                      _isLogin ? 'Create one' : 'Sign in',
                      style: const TextStyle(color: Color(0xFF6366F1),
                          fontWeight: FontWeight.w700, fontSize: 13),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _label(String text) => Text(text,
      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700,
          color: Color(0xFF6B7280), letterSpacing: 0.8));

  Widget _field({
    required TextEditingController controller,
    required String hint,
    TextInputType inputType = TextInputType.text,
  }) {
    return TextField(
      controller: controller,
      keyboardType: inputType,
      style: const TextStyle(color: Colors.white, fontSize: 15),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: const TextStyle(color: Color(0x4DFFFFFF)),
        filled: true,
        fillColor: const Color(0x0AFFFFFF),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0x1AFFFFFF)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0x1AFFFFFF)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0x806366F1), width: 1.5),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
    );
  }

  Widget _pwField() {
    return TextField(
      controller: _pwCtrl,
      obscureText: !_showPw,
      style: const TextStyle(color: Colors.white, fontSize: 15),
      decoration: InputDecoration(
        hintText: '••••••••',
        hintStyle: const TextStyle(color: Color(0x4DFFFFFF)),
        filled: true,
        fillColor: const Color(0x0AFFFFFF),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: Color(0x1AFFFFFF))),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: Color(0x1AFFFFFF))),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: Color(0x806366F1), width: 1.5)),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        suffixIcon: GestureDetector(
          onTap: () => setState(() => _showPw = !_showPw),
          child: Icon(_showPw ? Icons.visibility_off : Icons.visibility,
              color: const Color(0x66FFFFFF), size: 20),
        ),
      ),
    );
  }
}
