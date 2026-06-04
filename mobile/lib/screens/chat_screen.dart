import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../services/auth_service.dart';

const String kApiBase = 'https://api.neurotwin.ai';

class Message {
  final String id;
  final String role;
  String content;
  final DateTime createdAt;
  final String? emotion;

  Message({
    required this.id,
    required this.role,
    required this.content,
    required this.createdAt,
    this.emotion,
  });
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});
  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final List<Message> _messages = [];
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scroll = ScrollController();
  bool _streaming = false;
  String? _sessionId;

  @override
  void initState() {
    super.initState();
    _createSession();
  }

  Future<void> _createSession() async {
    final token = await AuthService.instance.getAccessToken();
    final resp = await http.post(
      Uri.parse('$kApiBase/v1/conversation/session'),
      headers: {'Authorization': 'Bearer $token', 'Content-Type': 'application/json'},
      body: jsonEncode({}),
    );
    if (resp.statusCode == 200) {
      final data = jsonDecode(resp.body);
      setState(() => _sessionId = data['session_id']);
    }
  }

  Future<void> _sendMessage(String text) async {
    if (text.trim().isEmpty || _streaming || _sessionId == null) return;
    _controller.clear();

    final userMsg = Message(
      id: 'user_${DateTime.now().millisecondsSinceEpoch}',
      role: 'user',
      content: text,
      createdAt: DateTime.now(),
    );
    setState(() {
      _messages.add(userMsg);
      _streaming = true;
    });
    _scrollToBottom();

    // Add placeholder assistant message
    final astId = 'ast_${DateTime.now().millisecondsSinceEpoch}';
    final astMsg = Message(id: astId, role: 'assistant', content: '', createdAt: DateTime.now());
    setState(() => _messages.add(astMsg));

    final token = await AuthService.instance.getAccessToken();
    final request = http.Request(
      'POST',
      Uri.parse('$kApiBase/v1/conversation/$_sessionId/stream'),
    );
    request.headers.addAll({
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
    });
    request.body = jsonEncode({'content': text, 'session_id': _sessionId});

    try {
      final streamedResp = await http.Client().send(request);
      final stream = streamedResp.stream.transform(utf8.decoder);

      await for (final chunk in stream) {
        for (final line in chunk.split('\n')) {
          if (line.startsWith('data:')) {
            final raw = line.substring(5).trim();
            try {
              final evt = jsonDecode(raw);
              if (evt['type'] == 'token') {
                setState(() {
                  final idx = _messages.indexWhere((m) => m.id == astId);
                  if (idx >= 0) _messages[idx].content += evt['data'] as String;
                });
                _scrollToBottom();
              }
            } catch (_) {}
          }
        }
      }
    } catch (e) {
      debugPrint('Stream error: $e');
    } finally {
      setState(() => _streaming = false);
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF080C14),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Row(
          children: [
            Container(
              width: 36, height: 36,
              decoration: BoxDecoration(
                gradient: const LinearGradient(colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)]),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.auto_awesome, color: Colors.white, size: 18),
            ),
            const SizedBox(width: 10),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('NEUROTWIN', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: Colors.white, letterSpacing: 1)),
                Text('Your digital companion', style: TextStyle(fontSize: 11, color: Color(0xFF6B7280))),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(icon: const Icon(Icons.memory, color: Color(0xFF6366F1)), onPressed: () {}),
          IconButton(icon: const Icon(Icons.bar_chart, color: Color(0xFF6366F1)), onPressed: () {}),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: _messages.isEmpty
                ? _buildEmpty()
                : ListView.builder(
                    controller: _scroll,
                    padding: const EdgeInsets.all(16),
                    itemCount: _messages.length + (_streaming ? 1 : 0),
                    itemBuilder: (ctx, i) {
                      if (i == _messages.length) return _buildTyping();
                      return _buildBubble(_messages[i]);
                    },
                  ),
          ),
          _buildInputBar(),
        ],
      ),
    );
  }

  Widget _buildEmpty() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 64, height: 64,
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [Color(0x4D6366F1), Color(0x338B5CF6)]),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: const Color(0x4D8B5CF6)),
            ),
            child: const Icon(Icons.auto_awesome, color: Color(0xFF8B5CF6), size: 28),
          ),
          const SizedBox(height: 20),
          const Text("I'm your NEUROTWIN",
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: Colors.white)),
          const SizedBox(height: 8),
          const Text("What's on your mind?",
              style: TextStyle(fontSize: 14, color: Color(0xFF6B7280))),
        ],
      ),
    );
  }

  Widget _buildBubble(Message msg) {
    final isUser = msg.role == 'user';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!isUser)
            Container(
              width: 28, height: 28, margin: const EdgeInsets.only(right: 8),
              decoration: BoxDecoration(
                gradient: const LinearGradient(colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)]),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.auto_awesome, color: Colors.white, size: 14),
            ),
          Flexible(
            child: Container(
              constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                gradient: isUser
                    ? const LinearGradient(colors: [Color(0x336366F1), Color(0x268B5CF6)])
                    : null,
                color: isUser ? null : const Color(0x0FFFFFFF),
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(16),
                  topRight: const Radius.circular(16),
                  bottomLeft: Radius.circular(isUser ? 16 : 4),
                  bottomRight: Radius.circular(isUser ? 4 : 16),
                ),
                border: Border.all(
                  color: isUser ? const Color(0x406366F1) : const Color(0x14FFFFFF),
                ),
              ),
              child: msg.content.isEmpty
                  ? const SizedBox(
                      width: 40, height: 16,
                      child: LinearProgressIndicator(
                        backgroundColor: Color(0x206366F1),
                        color: Color(0xFF6366F1),
                        minHeight: 2,
                      ),
                    )
                  : Text(
                      msg.content,
                      style: const TextStyle(color: Color(0xE2FFFFFF), fontSize: 15, height: 1.6),
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTyping() {
    return Row(
      children: [
        Container(
          width: 28, height: 28, margin: const EdgeInsets.only(right: 8),
          decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)]),
            borderRadius: BorderRadius.circular(8),
          ),
          child: const Icon(Icons.auto_awesome, color: Colors.white, size: 14),
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: const Color(0x0FFFFFFF),
            borderRadius: const BorderRadius.only(
              topLeft: Radius.circular(16), topRight: Radius.circular(16),
              bottomRight: Radius.circular(16), bottomLeft: Radius.circular(4),
            ),
            border: Border.all(color: const Color(0x14FFFFFF)),
          ),
          child: const Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              _Dot(delay: 0), SizedBox(width: 4),
              _Dot(delay: 200), SizedBox(width: 4),
              _Dot(delay: 400),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildInputBar() {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: Color(0x0FFFFFFF))),
        color: Color(0xFF080C14),
      ),
      child: Row(
        children: [
          Expanded(
            child: Container(
              decoration: BoxDecoration(
                color: const Color(0x0AFFFFFF),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0x14FFFFFF)),
              ),
              child: TextField(
                controller: _controller,
                style: const TextStyle(color: Colors.white, fontSize: 15),
                decoration: const InputDecoration(
                  hintText: 'Say something…',
                  hintStyle: TextStyle(color: Color(0x4DFFFFFF)),
                  border: InputBorder.none,
                  contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                ),
                onSubmitted: _sendMessage,
                textInputAction: TextInputAction.send,
              ),
            ),
          ),
          const SizedBox(width: 10),
          GestureDetector(
            onTap: () => _sendMessage(_controller.text),
            child: Container(
              width: 46, height: 46,
              decoration: BoxDecoration(
                gradient: const LinearGradient(colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)]),
                borderRadius: BorderRadius.circular(13),
              ),
              child: const Icon(Icons.send_rounded, color: Colors.white, size: 18),
            ),
          ),
        ],
      ),
    );
  }
}

class _Dot extends StatefulWidget {
  final int delay;
  const _Dot({required this.delay});
  @override
  State<_Dot> createState() => _DotState();
}

class _DotState extends State<_Dot> with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 600));
    _anim = Tween(begin: 0.0, end: 1.0).animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut));
    Future.delayed(Duration(milliseconds: widget.delay), () {
      if (mounted) _ctrl.repeat(reverse: true);
    });
  }

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _anim,
      builder: (_, __) => Transform.translate(
        offset: Offset(0, -4 * _anim.value),
        child: Container(
          width: 7, height: 7,
          decoration: BoxDecoration(
            color: Color.lerp(const Color(0x998B5CF6), const Color(0xFFA78BFA), _anim.value),
            borderRadius: BorderRadius.circular(4),
          ),
        ),
      ),
    );
  }
}
