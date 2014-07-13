import time
import socket
import datetime

from jaraco.util import timing

def client_host(server_host):
	"""Return the host on which a client can connect to the given listener."""
	if server_host == '0.0.0.0':
		# 0.0.0.0 is INADDR_ANY, which should answer on localhost.
		return '127.0.0.1'
	if server_host in ('::', '::0', '::0.0.0.0'):
		# :: is IN6ADDR_ANY, which should answer on localhost.
		# ::0 and ::0.0.0.0 are non-canonical but common
		# ways to write IN6ADDR_ANY.
		return '::1'
	return server_host


def _check_port(host, port, timeout=1.0):
	"""
	Raise an error if the given port is not free on the given host.
	"""
	if not host:
		raise ValueError("Host values of '' or None are not allowed.")
	host = client_host(host)
	port = int(port)

	# AF_INET or AF_INET6 socket
	# Get the correct address family for host (allows IPv6 addresses)
	try:
		info = socket.getaddrinfo(host, port, socket.AF_UNSPEC,
			socket.SOCK_STREAM)
	except socket.gaierror:
		if ':' in host:
			info = [(
				socket.AF_INET6, socket.SOCK_STREAM, 0, "", (host, port, 0, 0)
			)]
		else:
			info = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (host, port))]

	for res in info:
		af, socktype, proto, canonname, sa = res
		s = None
		try:
			s = socket.socket(af, socktype, proto)
			# See http://groups.google.com/group/cherrypy-users/
			#        browse_frm/thread/bbfe5eb39c904fe0
			s.settimeout(timeout)
			s.connect((host, port))
			s.close()
		except socket.error:
			if s:
				s.close()
		else:
			raise IOError("Port %s is in use on %s; perhaps the previous "
				"httpserver did not shut down properly." %
				(repr(port), repr(host)))


class Timeout(IOError):
	pass


def wait_for_free_port(host, port, timeout=float('Inf')):
	"""
	Wait for the specified port to become free (dropping or rejecting
	requests). Return when the port is free or raise a Timeout if timeout has
	elapsed.

	Timeout may be specified in seconds or as a timedelta.
	If timeout is None or ∞, the routine will run indefinitely.
	"""
	if not host:
		raise ValueError("Host values of '' or None are not allowed.")

	if isinstance(timeout, datetime.timedelta):
		timeout = timeout.total_seconds()

	if timeout is None:
		# treat None as infinite timeout
		timeout = float('Inf')

	watch = timing.Stopwatch()

	while watch.split().total_seconds() < timeout:
		try:
			# Expect a free port, so use a small timeout
			_check_port(host, port, timeout=0.1)
			return
		except IOError:
			# Politely wait.
			time.sleep(0.1)

	raise Timeout("Port {port} not free on {host}".format(**vars()))


def wait_for_occupied_port(host, port, timeout=float('Inf')):
	"""
	Wait for the specified port to become occupied (accepting requests).
	Return when the port is occupied or raise a Timeout if timeout has
	elapsed.

	Timeout may be specified in seconds or as a timedelta.
	If timeout is None or ∞, the routine will run indefinitely.
	"""
	if not host:
		raise ValueError("Host values of '' or None are not allowed.")

	if isinstance(timeout, datetime.timedelta):
		timeout = timeout.total_seconds()

	if timeout is None:
		# treat None as infinite timeout
		timeout = float('Inf')

	watch = timing.Stopwatch()

	while watch.split().total_seconds() < timeout:
		try:
			_check_port(host, port, timeout=.5)
			# Politely wait
			time.sleep(0.1)
		except IOError:
			# port is occupied
			return

	raise Timeout("Port {port} not bound on {host}".format(**vars))
