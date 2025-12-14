# Calendar

## Project Description

Calendar is a robust and user-friendly application designed to streamline the management of events and schedules, drawing inspiration from Google Calendar. It serves as a comprehensive tool that allows users to create, edit, view, and delete events with ease. Additionally, it facilitates inviting participants to events, responding to invitations, setting reminders, sharing events, and viewing shared calendars. The platform is built to cater to individual users' needs, ensuring a seamless scheduling experience.

## Quick Start

To get Calendar up and running with minimal setup, we have containerized the application using Docker. Ensure you have Docker and docker-compose installed on your machine. Then, follow these steps:

1. Clone the repository to your local machine.
2. Navigate to the root directory of the project.
3. Run the following command to start the application:

```sh
docker-compose up -d
```

This will pull the necessary images, build the service, and start the application. Access the application through your web browser at the designated port.

## API Endpoints

Calendar exposes several RESTful endpoints to interact with the application programmatically:

- **User Management**
  - `POST /api/users/`: Create a new user account.
  - `GET /api/users/{userId}/`: Retrieve a user's details.

- **Event Management**
  - `POST /api/events/`: Create a new event.
  - `GET /api/events/{eventId}/`: Get details of a specific event.
  - `PUT /api/events/{eventId}/`: Update an existing event.
  - `DELETE /api/events/{eventId}/`: Delete an event.
  - `GET /api/events/`: List all events for the user.

- **Invitations**
  - `POST /api/invitations/`: Send an invitation to a user.
  - `POST /api/invitations/{invitationId}/respond`: Respond to an invitation.

- **Reminders**
  - `POST /api/reminders/`: Set a reminder for an event.

## OpenEnv Usage Example

To manage environment variables efficiently, Calendar uses OpenEnv. Here’s an example of how to configure OpenEnv for the application:

1. Install OpenEnv if you haven’t already.
2. In the project root, create a file named `.env` for your environment variables.
3. Add your configuration variables. For instance:

```env
DB_HOST=localhost
DB_USER=username
DB_PASS=password
PORT=3000
```

4. Access these variables in your application using the OpenEnv library.

## Project Structure

The Calendar application is structured as follows:

- `/api` - Contains the API controllers and routes.
- `/models` - Includes the data models (User, Event, Invitation, Reminder).
- `/services` - Holds the business logic for handling entities.
- `/config` - Configuration files and environment-specific settings.
- `/db` - Database migrations and seed scripts.
- `/tests` - Automated tests for the application.
- `docker-compose.yml` - Docker compose file to containerize the application.
- `.env.example` - An example `.env` file.

This structure is designed to promote modularity and ease of maintenance.

## Development Setup

To set up the Calendar application for development, follow these steps:

1. Ensure you have Node.js and a database (e.g., PostgreSQL) installed.
2. Clone the repository and navigate into the project directory.
3. Install dependencies:

```sh
npm install
```

4. Set up your environment variables by copying `.env.example` to `.env` and adjusting the values accordingly.
5. Run database migrations:

```sh
npm run db:migrate
```

6. Start the development server:

```sh
npm run dev
```

7. The application should now be running on `localhost` at the port specified in your `.env` file.

## Contributing

Contributions to Calendar are welcome! Please refer to the CONTRIBUTING.md file for guidelines on how to contribute to this project.

## License

This project is licensed under the MIT License - see the LICENSE file for details.