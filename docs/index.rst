Smart Meeting Room Management System Documentation
==================================================

Welcome to the Smart Meeting Room Management System documentation.

This system provides a comprehensive microservices-based backend for managing meeting room bookings, reviews, and resource allocation.

Team Members
-----------

* **Ahmad Yateem** - Users Service & Bookings Service
* **Hassan Fouani** - Rooms Service & Reviews Service

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   services
   database
   utilities
   api_reference

Services Overview
-----------------

The system consists of four main microservices:

1. **Users Service** (Port 5001) - Authentication and user management
2. **Rooms Service** (Port 5002) - Meeting room inventory management
3. **Bookings Service** (Port 5003) - Booking creation and management
4. **Reviews Service** (Port 5004) - Review and rating management

API Reference
=============

Services
--------

.. automodule:: services.users.app
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: services.rooms.app
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: services.bookings.app
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: services.reviews.app
   :members:
   :undoc-members:
   :show-inheritance:

Database Models
--------------

.. automodule:: database.models
   :members:
   :undoc-members:
   :show-inheritance:

Utilities
---------

.. automodule:: utils.auth
   :members:
   :undoc-members:

.. automodule:: utils.validators
   :members:
   :undoc-members:

.. automodule:: utils.sanitizers
   :members:
   :undoc-members:

.. automodule:: utils.cache
   :members:
   :undoc-members:

.. automodule:: utils.circuit_breaker
   :members:
   :undoc-members:

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
